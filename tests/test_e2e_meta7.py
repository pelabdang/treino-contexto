"""QA de ponta a ponta da Meta 7, a semana-padrao, o tipo de treino e a linha de base (issue #271, ADR 0011).

Segue o roteiro de `docs/produto/meta-7-como-rodar.md`: migracoes (alembic, ate a 0011) -> as 81 atividades sinteticas
de `tests/fixtures/meta7/` com a regra de reserva (`aplicar_tipos`, como numa importacao, ainda sem plano) -> API
(TestClient): `PUT` das duas vigencias da semana-padrao -> tipo, origem e divergencia de cada atividade contra o oraculo
`TIPO_ESPERADO` -> `linha_base@2` contra `LINHA_BASE_ESPERADA` e `SEM_LINHA_BASE` -> idempotencia, passado intacto, tipo
confirmado intocado, nada gravado na leitura -> `worker.reclassificar` num segundo atleta, com blocos de FIT de verdade.
Num SQLite temporario; so dado sintetico. Sem rede: os subprocessos rodam com uma guarda de socket (`sitecustomize`) e o
teste tem a mesma guarda.

Os testes seguem a ordem do arquivo e dividem o mesmo banco (como os e2e das Metas 2 a 6), entao a ordem importa.
"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "tests" / "fixtures" / "meta7"
FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"
API = RAIZ / "services" / "api"

GUARDA = '''"""Guarda de rede dos subprocessos do e2e: so conexao local."""
import socket

_LOCAIS = ("localhost", "127.0.0.1", "::1")
_connect, _create, _getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo


def _host(e):
    return e[0] if isinstance(e, tuple) else e


def _bloqueia():
    raise AssertionError("comando tentou abrir conexao de rede")


def _c(self, e, *a, **k):
    if _host(e) not in _LOCAIS and self.family != socket.AF_UNIX:
        _bloqueia()
    return _connect(self, e, *a, **k)


def _cc(e, *a, **k):
    if _host(e) not in _LOCAIS:
        _bloqueia()
    return _create(e, *a, **k)


def _g(h, *a, **k):
    if h is not None and h not in _LOCAIS:
        _bloqueia()
    return _getaddr(h, *a, **k)


socket.socket.connect, socket.create_connection, socket.getaddrinfo = _c, _cc, _g
'''


def _carregar(nome, caminho):
    if str(API) not in sys.path:
        sys.path.insert(0, str(API))
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


O = _carregar("oraculo_meta7_e2e", PASTA / "oraculo.py")
FIXTURES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
VIGENCIAS = json.loads((PASTA / "semana_padrao.json").read_text(encoding="utf-8"))["vigencias"]
PROTEGIDAS = ("professor", "trainingpeaks")


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local, tambem dentro do processo do teste."""
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def _host(e):
        return e[0] if isinstance(e, tuple) else e

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def connect_(self, e, *a, **k):
        if _host(e) not in locais and self.family != socket.AF_UNIX:
            bloqueia()
        return connect(self, e, *a, **k)

    def create_(e, *a, **k):
        if _host(e) not in locais:
            bloqueia()
        return create(e, *a, **k)

    def getaddr_(h, *a, **k):
        if h is not None and h not in locais:
            bloqueia()
        return getaddr(h, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect_)
    monkeypatch.setattr(socket, "create_connection", create_)
    monkeypatch.setattr(socket, "getaddrinfo", getaddr_)


def _roda(args, env, cwd=RAIZ, esperado=0):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == esperado, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r


def _blocos(a, estrutura, tiros):
    """Os blocos de verdade a partir do resumo `estrutura` das fixtures (como o passo 3 do guia)."""
    from app.db.models import BlocoAtividade
    from app.metricas import esforcos as ef

    def b(ordem, cat, dur, dist, fc=None, faixa=None):
        a.blocos.append(BlocoAtividade(
            ordem=ordem, categoria=cat, volta_inicial=ordem, volta_final=ordem, inicio_offset_s=0.0, duracao_s=dur,
            distancia_m=dist, fc_media=fc, pace_s_km=dur / dist * 1000, faixa=faixa, versao_deteccao=ef.VERSAO))

    if estrutura == "sem_esforco":
        b(0, "leve", a.duracao_s, a.distancia_m)
    elif estrutura == "esforco":
        b(0, "aquecimento", 600, 1500)
        b(1, "esforco", 300, 1000, None, "d1500")
        b(2, "desaquecimento", 600, 1500)
    elif estrutura == "tiros":
        b(0, "aquecimento", 600, 1500)
        ordem = 1
        for _ in range(tiros["n"]):
            b(ordem, "esforco", tiros["melhor_pace_s_km"], 1000, tiros["fc_melhor_tiro"], "d1000")
            b(ordem + 1, "recuperacao", 200, 500)
            ordem += 2
        b(ordem, "desaquecimento", 600, 1500)


def _importa_fixtures(eng):
    """O passo 3 do guia: 81 atividades, blocos, carga e transicao, e a regra de reserva (sem semana-padrao)."""
    from app.db.models import Atividade, Atleta, CargaAtividade, RotuloTransicao
    from app.metricas import carga as cg
    from app.servicos.tipo_treino import aplicar_tipos

    with Session(eng) as s:
        atleta = Atleta(nome="Atleta Ficticio")
        s.add(atleta)
        s.flush()
        for f in FIXTURES:
            a = Atividade(
                atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
                inicio=datetime.fromisoformat(f["inicio"]), fuso_min=f["fuso_min"], duracao_s=f["duracao_s"],
                distancia_m=f["distancia_m"], fc_media=f["fc_media"], tipo_treino=f["tipo_treino"],
                tipo_origem=f["tipo_origem"], tipo_confirmado=f["tipo_confirmado"])
            s.add(a)
            _blocos(a, f["estrutura"], f["tiros"])
            if f["carga"] is not None:
                a.carga = CargaAtividade(
                    estado="calculada", carga=f["carga"], metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                    entrada="x" * 64, versao=cg.VERSAO, calculado_em=datetime(2026, 4, 1, tzinfo=UTC))
            if f["transicao"]:
                a.rotulo_transicao = RotuloTransicao(
                    transicao=True, origem="atleta", definido_em=datetime(2026, 4, 1, tzinfo=UTC))
        s.flush()
        aplicar_tipos(s, atleta.id)
        s.commit()
        return atleta.id


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.session import get_session
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    base = tmp_path_factory.mktemp("e2e_meta7")
    guarda = base / "guarda"
    guarda.mkdir()
    (guarda / "sitecustomize.py").write_text(GUARDA, encoding="utf-8")
    url = f"sqlite:///{base / 'treino.db'}"
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(guarda)}
    env.pop("VIRTUAL_ENV", None)
    r = subprocess.run(
        [sys.executable, "-c", "import socket; socket.create_connection(('example.com', 80), timeout=1)"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0 and "conexao de rede" in r.stderr  # a guarda vale mesmo
    r = _roda(["-m", "alembic", "upgrade", "head"], env, API)
    _roda(["-m", "alembic", "current"], env, API)
    eng = create_engine(url)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: base / "fit"
    try:
        yield {"client": TestClient(app), "eng": eng, "env": env, "base": base, "app": app, "saidas": []}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _get(ctx, caminho, status=200):
    r = ctx["client"].get(caminho)
    assert r.status_code == status, (caminho, r.status_code, r.text[:300])
    return r


def _put(ctx, atleta, corpo, status=200):
    r = ctx["client"].put(f"/atletas/{atleta}/semana-padrao", json=corpo)
    assert r.status_code == status, (r.status_code, r.text[:300])
    return r.json()


def _ids(ctx, atleta=1):
    """fonte_id (ex.: '2026-03-13/cor1') -> id da atividade no banco."""
    return {f: i for i, f in _sql(ctx, "select id, fonte_id from atividade where atleta_id = :a", a=atleta)}


def _atividade(ctx, atleta, atividade):
    return _get(ctx, f"/atletas/{atleta}/atividades/{atividade}").json()


def _origens(ctx, atleta=1):
    return dict(_sql(ctx, "select coalesce(tipo_origem,'(sem)'), count(*) from atividade where atleta_id = :a group by 1", a=atleta))


def _tipos(ctx, atleta=1):
    return {f: (t, o, d) for f, t, o, d in _sql(
        ctx, "select fonte_id, tipo_treino, tipo_origem, tipo_divergencia from atividade where atleta_id = :a", a=atleta)}


def _esperado_do_oraculo(f):
    """(tipo, origem, divergencia) esperados; a divergencia do banco guarda so o motivo."""
    tipo, origem, div = O.TIPO_ESPERADO[f]
    return tipo, origem, (div if isinstance(div, str) or div is None else div.get("motivo"))


# ---------------------------------------------------------------- migracao e carga

def test_01_migracao_0011_cria_as_tabelas_e_as_colunas(ctx):
    assert _sql(ctx, "select version_num from alembic_version") == [("0011",)]
    tabelas = {t for (t,) in _sql(ctx, "select name from sqlite_master where type = 'table'")}
    assert {"semana_padrao", "semana_padrao_item"} <= tabelas
    colunas = {c[1] for c in _sql(ctx, "pragma table_info(atividade)")}
    assert {"tipo_versao", "tipo_divergencia", "tipo_origem", "tipo_confirmado"} <= colunas


def test_02_carga_das_81_atividades_e_so_a_regra_de_reserva(ctx):
    assert len(FIXTURES) == 81
    assert _importa_fixtures(ctx["eng"]) == 1
    assert _origens(ctx) == {"(sem)": 40, "professor": 1, "sugestao": 39, "trainingpeaks": 1}
    # sem plano nao ha semana-padrao nem divergencia
    j = _get(ctx, "/atletas/1/semana-padrao").json()
    assert j["vigente"] is None and j["vigencias"] == []
    assert _sql(ctx, "select count(*) from atividade where tipo_divergencia is not null") == [(0,)]


def test_03_antes_do_plano_as_duas_atividades_do_guia_tem_so_a_reserva(ctx):
    ids = _ids(ctx)
    for chave, tipo in (("2026-03-13/cor1", "leve"), ("2026-03-17/cor1", "intervalado")):
        j = _atividade(ctx, 1, ids[chave])
        assert (j["tipo_treino"], j["tipo_origem"]) == (tipo, "sugestao")
        lb = j["linha_base"]
        assert (lb["versao"], lb["estado"], lb["janela_semanas"], lb["minimo_treinos"]) == ("linha_base@2", "ok", 12, 8)
    pace = {m["chave"]: m for m in _atividade(ctx, 1, ids["2026-03-13/cor1"])["linha_base"]["metricas"]}
    assert (pace["pace_medio"]["estado"], pace["pace_medio"]["n"]) == ("fora", 12)  # ainda nao e o do oraculo
    assert pace["fc_media"]["n"] == 9


# ---------------------------------------------------------------- semana-padrao

def test_04_primeira_vigencia_reaplica_46(ctx):
    j = _put(ctx, 1, VIGENCIAS[0])
    assert (j["vigente_desde"], j["definido_por"], len(j["itens"]), j["atividades_reaplicadas"]) == ("2026-01-05", "atleta", 7, 46)


def test_05_segunda_vigencia_reaplica_so_de_02_03_em_diante(ctx):
    j = _put(ctx, 1, VIGENCIAS[1])
    assert (j["vigente_desde"], j["definido_por"], j["atividades_reaplicadas"]) == ("2026-03-02", "professor", 8)
    assert _origens(ctx) == {"(sem)": 14, "professor": 1, "semana_padrao": 50, "sugestao": 15, "trainingpeaks": 1}


def test_06_get_da_semana_padrao_vigente_vigencias_e_texto_do_dia(ctx):
    j = _get(ctx, "/atletas/1/semana-padrao").json()
    assert j["vigente"]["vigente_desde"] == "2026-03-02" and j["vigente"]["definido_por"] == "professor"
    assert [v["vigente_desde"] for v in j["vigencias"]] == ["2026-03-02", "2026-01-05"]  # a mais nova primeiro
    textos = [i["dia_semana_texto"] for i in j["vigente"]["itens"]]
    assert textos == ["segunda", "terça", "quarta", "quinta", "sábado", "sábado", "domingo"]  # sexta sem treino


def test_07_regravar_o_mesmo_corpo_nao_reaplica_nada(ctx):
    antes = _tipos(ctx)
    assert _put(ctx, 1, VIGENCIAS[1])["atividades_reaplicadas"] == 0
    assert _put(ctx, 1, VIGENCIAS[0])["atividades_reaplicadas"] == 0
    assert _tipos(ctx) == antes
    assert len(_get(ctx, "/atletas/1/semana-padrao").json()["vigencias"]) == 2  # nao duplica a vigencia


def test_08_corpo_invalido_da_422_e_atleta_inexistente_da_404(ctx):
    _put(ctx, 1, {**VIGENCIAS[0], "definido_por": "ninguem"}, status=422)
    _put(ctx, 1, {**VIGENCIAS[0], "itens": [{"dia_semana": 9, "modalidade": "corrida", "tipo_treino": None}]}, status=422)
    _get(ctx, "/atletas/99/semana-padrao", status=404)
    assert len(_get(ctx, "/atletas/1/semana-padrao").json()["vigencias"]) == 2  # o erro nao gravou nada


# ---------------------------------------------------------------- tipo, origem e divergencia

def test_09_os_81_tipos_origens_e_divergencias_batem_com_o_oraculo(ctx):
    obtido = _tipos(ctx)
    assert set(obtido) == set(O.TIPO_ESPERADO) and len(obtido) == 81
    diferencas = {f: (obtido[f], _esperado_do_oraculo(f)) for f in obtido if obtido[f] != _esperado_do_oraculo(f)}
    assert diferencas == {}


def test_10_tipo_confirmado_nunca_muda(ctx):
    """Confirmado pelo atleta, `professor` e `trainingpeaks`: o plano e a regra nao tocam (caso E13 do oraculo)."""
    protegidas = [f for f in FIXTURES if f["tipo_confirmado"] or f["tipo_origem"] in PROTEGIDAS]
    assert {f["id"] for f in protegidas} == {"2026-01-08/cor1", "2026-01-15/cor1", "2026-01-29/cor1"}
    obtido = _tipos(ctx)
    for f in protegidas:
        assert obtido[f["id"]][:2] == (f["tipo_treino"], f["tipo_origem"]), f["id"]
    j = _atividade(ctx, 1, _ids(ctx)["2026-01-15/cor1"])  # terca? o plano diria outra coisa; o confirmado vence
    assert j["tipo_confirmado"] is True and j["tipo_treino"] == "moderado"


def test_11_a_semana_padrao_vence_a_regra_e_o_dia_sem_plano_cai_na_regra(ctx):
    ids = _ids(ctx)
    sexta = _atividade(ctx, 1, ids["2026-03-13/cor1"])  # sexta, sem item no plano
    assert (sexta["tipo_treino"], sexta["tipo_origem"], sexta["tipo_divergencia"]) == ("leve", "sugestao", None)
    terca = _atividade(ctx, 1, ids["2026-03-17/cor1"])  # terca, plano intervalado
    assert (terca["tipo_treino"], terca["tipo_origem"]) == ("intervalado", "semana_padrao")
    quarta = _atividade(ctx, 1, ids["2026-03-18/cic1"])  # ciclismo leve pelo plano
    assert (quarta["tipo_treino"], quarta["tipo_origem"]) == ("leve", "semana_padrao")


def test_12_divergencia_e_so_dado_o_plano_vence_o_tipo(ctx):
    ids = _ids(ctx)
    j = _atividade(ctx, 1, ids["2026-01-13/cor1"])
    assert j["tipo_treino"] == "intervalado"
    assert j["tipo_divergencia"] == {
        "motivo": "sem_esforco", "texto": "O plano diz intervalado, mas o treino não teve esforço detectado."}
    assert j["linha_base"]["estado"] == "sem_linha_base" and j["linha_base"]["motivo"] == "divergente"
    j = _atividade(ctx, 1, ids["2026-03-28/cor1"])
    assert j["tipo_treino"] == "longo"
    assert j["tipo_divergencia"]["motivo"] == "tem_tiros"
    assert j["tipo_divergencia"]["texto"] == "O plano diz longo, mas o treino teve 6 tiros de 1 km."


def test_13_plano_novo_vale_so_dali_para_frente_e_o_passado_nao_muda(ctx):
    antes = _tipos(ctx)
    nova = {"vigente_desde": "2026-12-01", "definido_por": "atleta",
            "itens": [{"dia_semana": 1, "modalidade": "natacao", "tipo_treino": "moderado"}]}
    j = _put(ctx, 1, nova)
    assert j["atividades_reaplicadas"] == 0  # nenhuma atividade sintetica e de 01/12 em diante
    assert _tipos(ctx) == antes
    assert [v["vigente_desde"] for v in _get(ctx, "/atletas/1/semana-padrao").json()["vigencias"]] == [
        "2026-12-01", "2026-03-02", "2026-01-05"]
    # a vigencia de hoje continua a de 02/03 (`em` e hoje, antes de 01/12)
    from datetime import date
    if date.today() < date(2026, 12, 1):
        assert _get(ctx, "/atletas/1/semana-padrao").json()["vigente"]["vigente_desde"] == "2026-03-02"


# ---------------------------------------------------------------- linha de base

def _metricas(ctx, chave):
    j = _atividade(ctx, 1, _ids(ctx)[chave])
    return j["linha_base"], {m["chave"]: m for m in j["linha_base"]["metricas"]}


@pytest.mark.parametrize("chave", sorted(O.LINHA_BASE_ESPERADA))
def test_14_linha_de_base_igual_ao_oraculo(ctx, chave):
    lb, ms = _metricas(ctx, chave)
    assert (lb["versao"], lb["estado"], lb["motivo"], lb["janela_semanas"], lb["minimo_treinos"]) == ("linha_base@2", "ok", None, 12, 8)
    esperado = O.LINHA_BASE_ESPERADA[chave]
    assert sorted(ms) == sorted(esperado)
    for nome, (estado, n, mediana, desvio, z) in esperado.items():
        m = ms[nome]
        assert (m["estado"], m["n"]) == (estado, n), (chave, nome)
        for campo, v in (("mediana", mediana), ("desvio", desvio), ("z", z)):
            if v is None:
                assert m[campo] is None, (chave, nome, campo)
            else:
                assert m[campo] == pytest.approx(v, abs=1e-3), (chave, nome, campo)


@pytest.mark.parametrize("chave", sorted(O.SEM_LINHA_BASE))
def test_15_sem_linha_de_base_traz_o_motivo(ctx, chave):
    lb, _ = _metricas(ctx, chave)
    assert lb["estado"] == "sem_linha_base" and lb["motivo"] == O.SEM_LINHA_BASE[chave]
    assert lb["metricas"] == [] and lb["texto"].startswith("Sem linha de base: ")


def test_16_textos_do_guia_passo_7(ctx):
    _, m68 = _metricas(ctx, "2026-03-13/cor1")
    assert m68["pace_medio"]["texto"] == (
        "Pace médio fora do seu normal para treino leve: 5:06/km, 24 s/km mais rápido que a mediana de 5:30/km "
        "(11 treinos nas últimas 12 semanas). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim.")
    assert (m68["fc_media"]["estado"], m68["fc_media"]["n"], m68["fc_media"]["valor_texto"]) == ("fora", 8, "160 bpm")
    assert (m68["carga_hora"]["estado"], m68["carga_hora"]["motivo"]) == ("sem_valor", "carga_pendente")
    _, m71 = _metricas(ctx, "2026-03-17/cor1")
    assert (m71["melhor_pace"]["estado"], m71["melhor_pace"]["valor_texto"], m71["melhor_pace"]["mediana_texto"]) == ("fora", "4:09/km", "4:24/km")
    assert m71["fc_melhor_tiro"]["estado"] == "dentro" and m71["fc_media"]["estado"] == "dentro"
    _, m72 = _metricas(ctx, "2026-03-18/cic1")
    assert (m72["carga_hora"]["estado"], m72["carga_hora"]["valor_texto"], m72["carga_hora"]["mediana_texto"]) == ("fora", "55,0 pontos/h", "42,0 pontos/h")


def test_17_a_sessao_nao_entra_na_propria_linha_de_base_e_a_leitura_nao_grava(ctx):
    antes = _sql(ctx, "select id, tipo_treino, tipo_origem, tipo_versao, tipo_divergencia, fc_media from atividade order by id")
    tabelas = {t for (t,) in _sql(ctx, "select name from sqlite_master where type = 'table'")}
    assert not any("linha_base" in t for t in tabelas)  # nao existe tabela para gravar a linha de base
    ids = _ids(ctx)
    for chave in sorted(O.LINHA_BASE_ESPERADA):
        _atividade(ctx, 1, ids[chave])
    assert _sql(ctx, "select id, tipo_treino, tipo_origem, tipo_versao, tipo_divergencia, fc_media from atividade order by id") == antes


def test_18_serie_de_tiros_continua_igual(ctx):
    """Regressao: a serie de tiros de 1 km nao depende do tipo nem da semana-padrao."""
    j = _get(ctx, "/atletas/1/evolucao/tiros-1km").json()
    assert j["atleta_id"] == 1 and j["reclassificacao_pendente"] in (True, False)
    assert j["metrica"] == "tiros_1km" and j["versao_calculo"] == "tiros_1km@6"
    assert j["eixos"]["pace"]["min_s_km"] == 249.0  # o melhor tiro das fixtures, igual ao do tipo intervalado


# ---------------------------------------------------------------- worker.reclassificar e FIT de verdade

def _worker(ctx, modulo, *args, esperado=0):
    r = _roda(["-m", f"worker.{modulo}", *args], ctx["env"], esperado=esperado)
    ctx["saidas"].append(r.stdout + r.stderr)
    return r.stdout


def test_20_segundo_atleta_com_fit_sintetico_e_plano_proprio(ctx):
    out = _worker(ctx, "importar_garmin", str(FIT), "--atleta", "Atleta Esforcos")
    assert "inseridas=7" in out
    ids = _ids(ctx, 2)
    assert len(ids) == 7
    antes = _sql(ctx, "select id, tipo_treino, tipo_origem from atividade where atleta_id = 2 order by id")
    assert sum(1 for _, t, o in antes if o == "sugestao") == 2  # as duas rodagens leves ganham a reserva na importacao
    corpo = {"vigente_desde": "2025-05-01", "definido_por": "atleta", "itens": [
        {"dia_semana": 1, "modalidade": "corrida", "tipo_treino": "longo"},
        {"dia_semana": 3, "modalidade": "corrida", "tipo_treino": "moderado"},
        {"dia_semana": 5, "modalidade": "corrida", "tipo_treino": "intervalado"}]}
    assert _put(ctx, 2, corpo)["atividades_reaplicadas"] == 4
    por_data = {d: (t, o, v) for d, t, o, v in _sql(
        ctx, "select substr(inicio,1,10), tipo_treino, tipo_origem, tipo_divergencia from atividade where atleta_id = 2")}
    assert por_data["2025-05-05"][:2] == ("longo", "semana_padrao")
    assert por_data["2025-05-07"][:2] == ("moderado", "semana_padrao")
    assert por_data["2025-05-09"] == ("intervalado", "semana_padrao", "sem_esforco")
    assert por_data["2025-05-10"][:2] == ("leve", "sugestao")
    assert por_data["2025-05-12"][:2] == ("longo", "semana_padrao")
    assert por_data["2025-05-14"][0] is None  # ciclismo, sem plano nem reserva
    # o atleta 1 nao foi tocado pelo plano do 2
    assert _origens(ctx, 1) == {"(sem)": 14, "professor": 1, "semana_padrao": 50, "sugestao": 15, "trainingpeaks": 1}


def test_21_atividades_do_atleta_2_na_api(ctx):
    ids = {d: i for i, d in _sql(ctx, "select id, substr(inicio,1,10) from atividade where atleta_id = 2")}
    j = _atividade(ctx, 2, ids["2025-05-09"])
    assert j["tipo_divergencia"]["motivo"] == "sem_esforco"
    assert (j["linha_base"]["estado"], j["linha_base"]["motivo"]) == ("sem_linha_base", "divergente")
    j = _atividade(ctx, 2, ids["2025-05-05"])
    assert j["linha_base"]["estado"] == "ok"
    ms = {m["chave"]: m for m in j["linha_base"]["metricas"]}
    assert (ms["pace_medio"]["estado"], ms["pace_medio"]["n"]) == ("aprendendo", 0)
    assert (ms["fc_media"]["estado"], ms["fc_media"]["n"]) == ("aprendendo", 0)
    j = _atividade(ctx, 2, ids["2025-05-14"])
    assert (j["linha_base"]["estado"], j["linha_base"]["motivo"]) == ("sem_linha_base", "sem_tipo")
    # um atleta nunca enxerga a atividade do outro
    _get(ctx, f"/atletas/1/atividades/{ids['2025-05-14']}", status=404)


def test_22_reclassificar_e_idempotente_e_zera_a_reclassificacao_pendente(ctx):
    ids = {d: i for i, d in _sql(ctx, "select id, substr(inicio,1,10) from atividade where atleta_id = 2")}
    _sql(ctx, "update atividade set tipo_versao = null where id = :i", i=ids["2025-05-10"])
    assert _get(ctx, "/atletas/2/evolucao/tiros-1km").json()["reclassificacao_pendente"] is True
    assert "reclassificadas 5 corridas do atleta 2" in _worker(ctx, "reclassificar", "--atleta-id", "2")
    assert _get(ctx, "/atletas/2/evolucao/tiros-1km").json()["reclassificacao_pendente"] is False
    depois = _sql(ctx, "select id, tipo_treino, tipo_origem, tipo_versao, tipo_divergencia from atividade where atleta_id = 2 order by id")
    assert "reclassificadas 5 corridas do atleta 2" in _worker(ctx, "reclassificar", "--atleta-id", "2")
    assert _sql(ctx, "select id, tipo_treino, tipo_origem, tipo_versao, tipo_divergencia from atividade where atleta_id = 2 order by id") == depois
    r = _roda(["-m", "worker.reclassificar", "--atleta-id", "99"], ctx["env"], esperado=1)
    assert "atleta 99 não encontrado" in r.stdout + r.stderr


def test_23_reclassificar_no_atleta_1_apaga_os_blocos_sinteticos_sem_voltas(ctx):
    """Documenta o aviso do passo 9 do guia: as atividades sinteticas nao tem voltas. Por ultimo: estraga o atleta 1."""
    antes = _sql(ctx, "select count(*) from bloco_atividade where atividade_id in (select id from atividade where atleta_id = 1)")[0][0]
    assert antes > 0
    _worker(ctx, "reclassificar", "--atleta-id", "1")
    assert _sql(ctx, "select count(*) from bloco_atividade where atividade_id in (select id from atividade where atleta_id = 1)") == [(0,)]
    assert _origens(ctx, 1).get("sugestao", 0) == 0


# ---------------------------------------------------------------- contrato e rede

def test_24_openapi_declara_semana_padrao_e_linha_base(ctx):
    spec = ctx["app"].openapi()
    assert "put" in spec["paths"]["/atletas/{atleta_id}/semana-padrao"]
    assert "get" in spec["paths"]["/atletas/{atleta_id}/semana-padrao"]
    esquemas = spec["components"]["schemas"]
    assert any("LinhaBase" in n for n in esquemas)
    gravado = json.loads((RAIZ / "packages" / "api-client" / "openapi.json").read_text(encoding="utf-8"))
    assert gravado["paths"]["/atletas/{atleta_id}/semana-padrao"] == spec["paths"]["/atletas/{atleta_id}/semana-padrao"]
    schema_ts = (RAIZ / "packages" / "api-client" / "src" / "schema.d.ts").read_text(encoding="utf-8")
    assert "semana-padrao" in schema_ts and "linha_base" in schema_ts


def test_25_nenhuma_saida_de_comando_cita_dado_real_ou_rede(ctx):
    assert ctx["saidas"], "nenhum comando rodou"
    for s in ctx["saidas"]:
        assert "conexao de rede" not in s
