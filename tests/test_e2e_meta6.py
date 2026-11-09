"""QA de ponta a ponta da Meta 6, a carga de treino (issue #146, ADR 0010).

Segue o fluxo do roteiro: migracoes (alembic, ate a 0010) -> importacao da exportacao sintetica de carga com dados de
saude (`worker.importar_garmin`, que chama `importar_saude` e `calcular_carga`) -> `worker.calcular_carga` -> API
(TestClient) conferida contra o oraculo `test_carga_oraculo.py` (carga@2: `ESPERADO`, `CARGA_DIA`, `SERIE`, `TOTAIS`) ->
idempotencia das duas rodadas (importar e calcular) -> versao e limiar novo recalculam -> grafico e conferencia
com o Garmin -> atleta sem saude -> nenhum valor de saude na API nem na saida dos comandos -> `worker.apagar_saude`.
Num SQLite temporario; so dado sintetico. Sem rede: os comandos rodam em subprocessos com uma guarda de socket
(`sitecustomize`) e o teste tem a mesma guarda.

Os testes seguem a ordem do arquivo e dividem o mesmo banco (como os e2e das Metas 2 a 5), entao a ordem importa.
"""

import csv
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures"
ZIP = FIXTURES / "garmin" / "carga" / "exportacao_carga.zip"
ZIP_SEM_SAUDE = FIXTURES / "garmin" / "carga" / "exportacao_carga_sem_saude.zip"
ORACULO = RAIZ / "services" / "api" / "tests" / "metricas" / "test_carga_oraculo.py"
API = RAIZ / "services" / "api"
ATLETA = "Atleta Carga Ficticio"
SEM_SAUDE = "Atleta Sem Saude Ficticio"
TOL = 1e-6
IGNORADAS = (4000000013, 4000000015, 4000000017)  # multiesporte_pai, troca, troca

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


def _oraculo():
    """Carrega o oraculo da #137 (conta feita a mao), sem duplicar as tabelas."""
    app = str(API)
    if app not in sys.path:
        sys.path.insert(0, app)
    spec = importlib.util.spec_from_file_location("oraculo_carga_e2e", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def orc():
    return _oraculo()


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local, tambem dentro do processo do teste."""
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def _host(endereco):
        return endereco[0] if isinstance(endereco, tuple) else endereco

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def connect_(self, endereco, *a, **k):
        if _host(endereco) not in locais and self.family != socket.AF_UNIX:
            bloqueia()
        return connect(self, endereco, *a, **k)

    def create_(endereco, *a, **k):
        if _host(endereco) not in locais:
            bloqueia()
        return create(endereco, *a, **k)

    def getaddr_(host, *a, **k):
        if host is not None and host not in locais:
            bloqueia()
        return getaddr(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect_)
    monkeypatch.setattr(socket, "create_connection", create_)
    monkeypatch.setattr(socket, "getaddrinfo", getaddr_)


def _roda(args, env, cwd=RAIZ, esperado=0):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == esperado, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.session import get_session
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    base = tmp_path_factory.mktemp("e2e_meta6")
    guarda = base / "guarda"
    guarda.mkdir()
    (guarda / "sitecustomize.py").write_text(GUARDA, encoding="utf-8")
    url = f"sqlite:///{base / 'treino.db'}"
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(guarda)}
    env.pop("VIRTUAL_ENV", None)
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem
    # a guarda vale mesmo: um subprocesso que tenta sair para a rede falha
    r = subprocess.run(
        [sys.executable, "-c", "import socket; socket.create_connection(('example.com', 80), timeout=1)"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0 and "conexao de rede" in r.stderr
    _roda(["-m", "alembic", "upgrade", "head"], env, API)
    eng = create_engine(url)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: base / "fit"
    try:
        yield {"client": TestClient(app), "eng": eng, "env": env, "base": base, "app": app}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _worker(ctx, modulo, *args, esperado=0):
    r = _roda(["-m", f"worker.{modulo}", *args], ctx["env"], esperado=esperado)
    ctx.setdefault("saidas", []).append(r.stdout + r.stderr)
    return r.stdout


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _get(ctx, caminho, status=200):
    r = ctx["client"].get(caminho)
    assert r.status_code == status, (caminho, r.status_code, r.text[:300])
    return r


def _ids(ctx, atleta_id=1):
    """fonte_id (numero do oraculo) -> id da atividade no banco."""
    return {int(f): i for i, f in _sql(ctx, "select id, fonte_id from atividade where atleta_id = :a", a=atleta_id)}


def _atividade(ctx, atleta, atividade):
    return _get(ctx, f"/atletas/{atleta}/atividades/{atividade}").json()


def _serie(ctx, atleta=1, qs=""):
    return _get(ctx, f"/atletas/{atleta}/carga{qs}").json()


def _carga_banco(ctx):
    return _sql(ctx, "select atividade_id, estado, carga, motivo, versao, entrada, calculado_em from carga_atividade order by atividade_id")


def _perto(a, b):
    return a is not None and b is not None and abs(a - b) <= TOL


# ---------------------------------------------------------------- 1. migracoes e importacao com saude
def test_1_migracoes_ate_a_0010(ctx):
    assert _sql(ctx, "select version_num from alembic_version") == [("0011",)]  # head; a 0011 (semana-padrao, #264) nao afeta o fluxo da Meta 6
    tabelas = {t for (t,) in _sql(ctx, "select name from sqlite_master where type = 'table'")}
    assert {"limiar_atleta", "zona_fc_atleta", "recorde_pessoal", "carga_garmin_dia", "carga_atividade"} <= tabelas


def test_2_importa_a_exportacao_de_carga_com_saude_e_calcula(ctx, orc):
    saida = _worker(ctx, "importar_garmin", str(ZIP), "--atleta", ATLETA)
    assert "saude limiar: inseridas=" in saida  # os dados de saude entraram na mesma importacao
    assert re.search(r"carga carga@2 do atleta 1", saida), saida  # e a carga foi calculada no fim
    assert _sql(ctx, "select count(*) from atividade") == [(23,)]
    assert _sql(ctx, "select count(*) from atleta") == [(1,)]
    assert _sql(ctx, "select count(*) from limiar_atleta")[0][0] > 0
    assert _sql(ctx, "select count(*) from zona_fc_atleta")[0][0] > 0
    assert _sql(ctx, "select count(*) from recorde_pessoal")[0][0] > 0
    assert _sql(ctx, "select count(*) from carga_garmin_dia")[0][0] > 0
    # 20 elegiveis com linha; os 3 multiesporte (pai e duas trocas) sem linha
    assert _sql(ctx, "select count(*) from carga_atividade") == [(20,)]
    ids = _ids(ctx)
    assert set(ids) == set(orc.ESPERADO) | set(IGNORADAS)
    com_linha = {a for (a,) in _sql(ctx, "select atividade_id from carga_atividade")}
    assert com_linha == {ids[i] for i in orc.ESPERADO}


def test_3_calcular_carga_de_novo_nao_muda_nada(ctx):
    antes = _carga_banco(ctx)
    saida = _worker(ctx, "calcular_carga", "--atleta-id", "1")
    assert "carga carga@2 do atleta 1" in saida
    assert "gravadas: 0" in saida and "calculadas: 13" in saida and "sem carga: 7" in saida, saida
    assert "ignoradas (multiesporte e troca, sem linha): 3" in saida
    assert _carga_banco(ctx) == antes  # nem valor, nem entrada, nem calculado_em


# ---------------------------------------------------------------- 2. API contra o oraculo
def test_4_serie_do_atleta_bate_com_o_oraculo(ctx, orc):
    j = _serie(ctx)
    assert j["atleta_id"] == 1 and j["versao"] == "serie_carga@1" and j["versao_carga"] == "carga@2"
    assert j["periodo"] is None and j["aviso"] is None
    dias = {date.fromisoformat(d["data"]): d for d in j["dias"]}
    assert len(dias) == len(j["dias"]) == 43  # 05/03 a 16/04, sem buracos
    assert min(dias) == orc.PRIMEIRO_DIA and max(dias) == orc.ULTIMO_DIA
    assert [d["data"] for d in j["dias"]] == sorted(d["data"] for d in j["dias"])
    for dia, d in dias.items():
        assert _perto(d["carga"], orc.CARGA_DIA.get(dia, 0.0)), (dia, d["carga"])
        assert d["tsb"] == pytest.approx(d["ctl"] - d["atl"], abs=1e-9)  # TSB do mesmo dia
    for dia, e in orc.SERIE.items():
        d = dias[dia]
        assert _perto(d["carga"], e.carga) and _perto(d["ctl"], e.ctl) and _perto(d["atl"], e.atl) and _perto(d["tsb"], e.tsb), dia
        assert (d["aprendendo"], d["atividades"], d["calculadas"], d["sem_carga"]) == (e.aprendendo, e.atividades, e.calculadas, e.sem_carga), dia


def test_5_historico_curto_ainda_aprendendo(ctx, orc):
    dias = _serie(ctx)["dias"]
    assert all(d["aprendendo"] for d in dias[:42])  # 05/03 a 15/04: menos de 42 dias desde o primeiro
    assert dias[42]["data"] == "2025-04-16" and dias[42]["aprendendo"] is False
    assert dias[0]["ctl"] < dias[0]["carga"]  # CTL parte de zero: um dia de carga nao a iguala


def test_6_totais_e_atividades_sem_carga_contadas(ctx, orc):
    t = _serie(ctx)["totais"]
    e = orc.TOTAIS
    assert t["atividades_importadas"] == e["atividades_importadas"] == 23
    assert t["calculadas"] == e["calculadas"] and t["sem_carga_total"] == e["sem_carga_total"]
    assert t["ignoradas_multiesporte"] == e["ignoradas_multiesporte"] and t["pendentes"] == 0
    assert t["por_motivo"] == e["por_motivo"]  # os seis motivos, sempre todos
    assert t["atividades_importadas"] == t["calculadas"] + t["sem_carga_total"] + t["pendentes"] + t["ignoradas_multiesporte"]
    # dias com treino sem dado nao sao descanso: 12/03 (esteira com cobertura baixa)
    dias = {d["data"]: d for d in _serie(ctx)["dias"]}
    assert dias["2025-03-12"]["sem_carga"] == 1 and dias["2025-03-12"]["calculadas"] == 0 and dias["2025-03-12"]["carga"] == 0
    assert dias["2025-03-09"]["atividades"] == 0 and dias["2025-03-09"]["sem_carga"] == 0  # descanso de verdade


def test_7_recorte_por_periodo_nao_muda_o_ctl(ctx):
    cheia = {d["data"]: d for d in _serie(ctx)["dias"]}
    j = _serie(ctx, qs="?inicio=2025-03-10&fim=2025-03-12")
    assert j["periodo"] == {"inicio": "2025-03-10", "fim": "2025-03-12"}
    assert [d["data"] for d in j["dias"]] == ["2025-03-10", "2025-03-11", "2025-03-12"]
    assert all(d == cheia[d["data"]] for d in j["dias"])  # CTL/ATL partem do primeiro dia, nao do recorte
    assert j["totais"] == _serie(ctx)["totais"]  # totais contam todas as atividades
    assert _serie(ctx, qs="?inicio=2030-01-01")["dias"] == []
    _get(ctx, "/atletas/1/carga?inicio=2025-04-01&fim=2025-03-01", 422)  # periodo invertido
    _get(ctx, "/atletas/1/carga?inicio=ontem", 422)
    _get(ctx, "/atletas/999/carga", 404)


def test_8_carga_de_cada_atividade_bate_com_o_oraculo_carga_2(ctx, orc):
    ids = _ids(ctx)
    for fonte, e in orc.ESPERADO.items():
        a = _atividade(ctx, 1, ids[fonte])
        c = a["carga"]
        assert c["versao"] == "carga@2", fonte
        assert c["estado"] == e.estado and c["motivo"] == e.motivo and c["metodo"] == e.metodo, (fonte, c)
        if e.estado == "calculada":
            assert _perto(c["carga"], e.carga), (fonte, c["carga"], e.carga)
            assert _perto(c["cobertura_pct"], e.cobertura_pct), fonte
        else:
            assert c["carga"] is None  # nunca carga inventada
            if e.motivo == "cobertura_insuficiente":
                assert _perto(c["cobertura_pct"], e.cobertura_pct)
        assert set(c) == {"estado", "carga", "metodo", "cobertura_pct", "motivo", "versao"}


def test_9_multiesporte_pai_e_troca_ficam_fora(ctx, orc):
    ids = _ids(ctx)
    subtipos = dict(_sql(ctx, "select fonte_id, subtipo from atividade where atleta_id = 1"))
    for fonte in IGNORADAS:
        assert subtipos[str(fonte)] in ("multiesporte_pai", "troca")
        assert _atividade(ctx, 1, ids[fonte])["carga"] is None  # sem carga e sem "sem carga": fora da conta
    assert {"multiesporte_pai", "troca"} <= set(subtipos.values())
    # as partes contam uma vez so: 15/03 tem natacao (sem carga), ciclismo e corrida (calculadas)
    dia = {d["data"]: d for d in _serie(ctx)["dias"]}["2025-03-15"]
    assert (dia["atividades"], dia["calculadas"], dia["sem_carga"]) == (3, 2, 1)
    assert _perto(dia["carga"], orc.CARGA_DIA[date(2025, 3, 15)])


def test_10_motivos_de_sem_carga(ctx, orc):
    motivos = {e.motivo for e in orc.ESPERADO.values() if e.estado == "sem_carga"}
    assert motivos == {"sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga"}
    # a data local decide o limiar: 4000000002 e das 22h locais de 04/03 (05/03 UTC) e fica sem limiar
    ids = _ids(ctx)
    assert _atividade(ctx, 1, ids[4000000002])["carga"]["motivo"] == "sem_limiar_na_data"
    assert _atividade(ctx, 1, ids[4000000002])["data_local"] == "2025-03-04"
    assert _atividade(ctx, 1, ids[4000000003])["carga"]["estado"] == "calculada"  # no dia em que o limiar comeca


# ---------------------------------------------------------------- 3. idempotencia e recalculo
def test_11_reimportar_nao_duplica_nem_muda_a_carga(ctx, orc):
    contagens = (
        "select (select count(*) from atividade), (select count(*) from segmento), (select count(*) from limiar_atleta), "
        "(select count(*) from zona_fc_atleta), (select count(*) from recorde_pessoal), "
        "(select count(*) from carga_garmin_dia), (select count(*) from carga_atividade), (select count(*) from atleta)"
    )
    antes, carga_antes = _sql(ctx, contagens), _carga_banco(ctx)
    saida = _worker(ctx, "importar_garmin", str(ZIP), "--atleta", ATLETA)
    assert "inseridas=0" in saida and "gravadas: 0" in saida, saida
    assert _sql(ctx, contagens) == antes
    assert _carga_banco(ctx) == carga_antes
    # e a saude sozinha, pelo comando proprio, tambem e idempotente
    saida = _worker(ctx, "importar_saude", str(ZIP), "--atleta", ATLETA)
    assert re.findall(r"inseridas=(\d+)", saida) == ["0"] * 4, saida
    assert _sql(ctx, contagens) == antes
    assert _serie(ctx)["totais"]["calculadas"] == orc.TOTAIS["calculadas"]


def test_12_mudar_a_versao_recalcula_tudo(ctx, orc):
    # simula uma versao antiga gravada: a API diz "pendente" e fora da serie, ate o comando recalcular
    ids = _ids(ctx)
    _sql(ctx, "update carga_atividade set versao = 'carga@1', carga = 1.0 where estado = 'calculada'")
    j = _serie(ctx)
    assert j["totais"]["pendentes"] == 13 and j["totais"]["calculadas"] == 0
    a = _atividade(ctx, 1, ids[4000000003])["carga"]
    assert a["estado"] == "pendente" and a["carga"] is None and a["versao"] is None
    saida = _worker(ctx, "calcular_carga", "--atleta-id", "1")
    assert "gravadas: 13" in saida and "calculadas: 13" in saida, saida
    assert _sql(ctx, "select count(distinct versao) from carga_atividade") == [(1,)]
    assert _serie(ctx)["totais"]["pendentes"] == 0
    assert _perto(_atividade(ctx, 1, ids[4000000003])["carga"]["carga"], orc.ESPERADO[4000000003].carga)


def test_13_limiar_novo_recalcula_so_o_que_usou(ctx, orc):
    antes = {a: (v, e) for a, _, v, _, _, e, _ in _carga_banco(ctx)}
    ids = _ids(ctx)
    original = _sql(ctx, "select id, valor from limiar_atleta where grandeza = 'velocidade_ms' and vigente_desde = '2025-03-10'")
    assert len(original) == 1
    lid, valor = original[0]
    _sql(ctx, "update limiar_atleta set valor = :v where id = :i", v=valor - 0.1, i=lid)
    _worker(ctx, "calcular_carga", "--atleta-id", "1")
    depois = {a: (v, e) for a, _, v, _, _, e, _ in _carga_banco(ctx)}
    mudou = {a for a in antes if antes[a][1] != depois[a][1]}
    # as calculadas por rTSS desde 10/03 usam o limiar de velocidade novo; as que tentaram o rTSS e cairam no hrTSS ou
    # em "sem pace" tambem regravam (a entrada da conta mudou), mas com o mesmo resultado; nada antes de 10/03 mexe
    rtss = {ids[i] for i, e in orc.ESPERADO.items() if e.metodo == "rtss" and e.dia >= date(2025, 3, 10)}
    depois_de_10_03 = {ids[i] for i, e in orc.ESPERADO.items() if e.dia >= date(2025, 3, 10)}
    assert rtss <= mudou <= depois_de_10_03, sorted(mudou)
    assert all(antes[a][0] != depois[a][0] for a in rtss)  # o valor da carga mudou so nas rTSS
    assert all(antes[a][0] == depois[a][0] for a in mudou - rtss)
    assert not _perto(_atividade(ctx, 1, ids[4000000008])["carga"]["carga"], orc.ESPERADO[4000000008].carga)
    # volta ao valor original: tudo volta ao oraculo
    _sql(ctx, "update limiar_atleta set valor = :v where id = :i", v=valor, i=lid)
    _worker(ctx, "calcular_carga", "--atleta-id", "1")
    assert {a: (v, e) for a, _, v, _, _, e, _ in _carga_banco(ctx)} == antes
    assert _perto(_atividade(ctx, 1, ids[4000000008])["carga"]["carga"], orc.ESPERADO[4000000008].carga)


# ---------------------------------------------------------------- 4. grafico e conferencia
def test_14_grafico_png_e_csv_da_serie(ctx, orc):
    pasta = ctx["base"] / "grafico"
    saida = _worker(ctx, "grafico_carga", "--atleta-id", "1", "--saida", str(pasta))
    png, arq = pasta / "carga-atleta-1.png", pasta / "carga-atleta-1.csv"
    assert f"gravado: {png}" in saida and f"gravado: {arq}" in saida
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    with arq.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert list(linhas[0]) == ["dia", "carga", "ctl", "atl", "tsb", "aprendendo", "atividades", "calculadas", "sem_carga"]
    assert len(linhas) == 43
    por_dia = {date.fromisoformat(r["dia"]): r for r in linhas}
    for dia, e in orc.SERIE.items():
        r = por_dia[dia]
        assert _perto(float(r["ctl"]), e.ctl) and _perto(float(r["atl"]), e.atl) and _perto(float(r["tsb"]), e.tsb), dia
        assert r["aprendendo"] == ("sim" if e.aprendendo else "nao")
    # o CSV bate com a API
    api = {d["data"]: d for d in _serie(ctx)["dias"]}
    assert all(_perto(float(r["ctl"]), api[r["dia"]]["ctl"]) for r in linhas)
    # recorte: o CTL do recorte e o da serie inteira
    _worker(ctx, "grafico_carga", "--atleta-id", "1", "--inicio", "2025-04-01", "--saida", str(ctx["base"] / "g2"))
    with (ctx["base"] / "g2" / "carga-atleta-1.csv").open(encoding="utf-8") as f:
        corte = list(csv.DictReader(f))
    assert corte[0]["dia"] == "2025-04-01" and _perto(float(corte[0]["ctl"]), api["2025-04-01"]["ctl"])
    _worker(ctx, "grafico_carga", "--atleta-id", "999", "--saida", str(pasta), esperado=1)


def test_15_conferencia_com_o_garmin(ctx):
    pasta = ctx["base"] / "conferencia"
    saida = _worker(ctx, "conferir_carga", "--atleta-id", "1", "--saida", str(pasta))
    assert "conferência" in saida
    for nome in ("conferencia-carga-atleta-1.csv", "conferencia-carga-atleta-1-resumo.csv", "conferencia-carga-atleta-1-cobertura.csv"):
        assert (pasta / nome).stat().st_size > 0, nome
    with (pasta / "conferencia-carga-atleta-1-cobertura.csv").open(encoding="utf-8") as f:
        cob = list(csv.DictReader(f))
    assert {r["regra"] for r in cob} == {"adr", "todos_os_dias"}
    assert all(int(r["dias_nossa"]) > 0 and int(r["dias_garmin"]) > 0 for r in cob)
    _worker(ctx, "conferir_carga", "--atleta-id", "999", "--saida", str(pasta), esperado=1)


# ---------------------------------------------------------------- 5. atleta sem saude
def test_16_atleta_sem_saude_fica_sem_carga_e_a_serie_vazia(ctx, orc):
    saida = _worker(ctx, "importar_garmin", str(ZIP_SEM_SAUDE), "--atleta", SEM_SAUDE)
    assert "sem carga: 20" in saida and "calculadas: 0" in saida, saida
    assert _sql(ctx, "select count(*) from limiar_atleta where atleta_id = 2") == [(0,)]  # nao estimou limiar
    ids = _ids(ctx, 2)
    assert len(ids) == 23
    for fonte, motivo in orc.SEM_SAUDE.items():
        c = _atividade(ctx, 2, ids[fonte])["carga"]
        assert (c["estado"], c["motivo"], c["carga"], c["metodo"]) == ("sem_carga", motivo, None, None), fonte
    for fonte in IGNORADAS:
        assert _atividade(ctx, 2, ids[fonte])["carga"] is None
    j = _serie(ctx, 2)
    assert j["dias"] == [] and j["aviso"] == "sem_carga_calculada"
    t, e = j["totais"], orc.TOTAIS_SEM_SAUDE
    assert t["calculadas"] == 0 and t["sem_carga_total"] == e["sem_carga_total"] and t["por_motivo"] == e["por_motivo"]
    assert t["ignoradas_multiesporte"] == 3 and t["atividades_importadas"] == 23
    # o grafico do atleta sem carga sai (vazio) e a serie do atleta 1 nao mudou
    pasta = ctx["base"] / "g_sem"
    _worker(ctx, "grafico_carga", "--atleta-id", "2", "--saida", str(pasta))
    assert (pasta / "carga-atleta-2.png").read_bytes()[:4] == b"\x89PNG"
    assert len(_serie(ctx, 1)["dias"]) == 43


# ---------------------------------------------------------------- 6. nenhum valor de saude na API nem nos comandos
def _chaves(o, achadas=None):
    achadas = set() if achadas is None else achadas
    if isinstance(o, dict):
        for k, v in o.items():
            achadas.add(k)
            _chaves(v, achadas)
    elif isinstance(o, list):
        for v in o:
            _chaves(v, achadas)
    return achadas


def test_17_nenhum_valor_de_saude_na_api(ctx, orc):
    proibidas = re.compile(r"limiar|zona|recorde|garmin|fc_max|fc_repouso|repouso|vigente|entrada", re.I)
    ids = _ids(ctx)
    atividades = [_atividade(ctx, 1, i) for i in ids.values()]

    def _suspeitas(r):  # "sem_limiar_na_data" e um motivo (chave de `por_motivo`), nao um dado de limiar
        return [k for k in _chaves(r) if proibidas.search(k) and k not in orc.MOTIVOS]

    respostas = [_serie(ctx), _serie(ctx, 2), _serie(ctx, qs="?inicio=2025-03-05"), *atividades]
    for r in respostas:
        assert not _suspeitas(r), r
    # os valores de saude gravados (limiar e carga do Garmin) nao aparecem como numero na carga nem na serie
    valores = {v for (v,) in _sql(ctx, "select valor from limiar_atleta")}
    valores |= {v for (v,) in _sql(ctx, "select carga_aguda from carga_garmin_dia where carga_aguda is not null")}
    valores = {v for v in valores if v >= 100 or v != int(v)}  # inteiros pequenos colidiriam com contagens
    assert valores

    def _numeros(o):
        if isinstance(o, dict):
            return [n for v in o.values() for n in _numeros(v)]
        if isinstance(o, list):
            return [n for v in o for n in _numeros(v)]
        return [o] if isinstance(o, (int, float)) and not isinstance(o, bool) else []

    achados = {n for r in [_serie(ctx), _serie(ctx, 2)] + [a["carga"] for a in atividades] for n in _numeros(r)}
    assert not (valores & achados)
    # o contrato: nenhum schema de carga publica campo de saude
    schemas = ctx["app"].openapi()["components"]["schemas"]
    for nome in ("CargaSerieOut", "DiaCargaOut", "TotaisCargaOut", "CargaAtividadeOut"):
        assert not [k for k in schemas[nome]["properties"] if proibidas.search(k)], nome


def test_18_comandos_nao_imprimem_valor_de_saude(ctx):
    valores = {v for (v,) in _sql(ctx, "select valor from limiar_atleta")}
    saidas = "\n".join(ctx["saidas"])
    tokens = set(re.findall(r"\d+(?:\.\d+)?", saidas))
    assert not ({f"{v:g}" for v in valores if v >= 10 or v != int(v)} & tokens)
    assert "aviso: dados de saude nao importados" not in saidas and "aviso: carga nao calculada" not in saidas


# ---------------------------------------------------------------- 7. contrato (OpenAPI e cliente)
def test_19_openapi_declara_a_carga_e_o_cliente_esta_de_acordo(ctx):
    spec = ctx["app"].openapi()
    op = spec["paths"]["/atletas/{atleta_id}/carga"]["get"]
    assert op["operationId"] == "cargaDoAtleta"
    assert "404" in op["responses"]
    versionado = json.loads((RAIZ / "packages" / "api-client" / "openapi.json").read_text(encoding="utf-8"))
    assert versionado["paths"]["/atletas/{atleta_id}/carga"] == spec["paths"]["/atletas/{atleta_id}/carga"]
    assert versionado["components"]["schemas"]["CargaAtividadeOut"] == spec["components"]["schemas"]["CargaAtividadeOut"]
    tipos = (RAIZ / "packages" / "api-client" / "src" / "schema.d.ts").read_text(encoding="utf-8")
    assert "cargaDoAtleta" in tipos and "CargaSerieOut" in tipos and "CargaAtividadeOut" in tipos


# ---------------------------------------------------------------- 8. apagar_saude
def test_20_apagar_saude_apaga_so_a_saude_e_a_carga_vira_sem_dados_de_saude(ctx, orc):
    n_ativ = _sql(ctx, "select count(*) from atividade where atleta_id = 1")
    _worker(ctx, "apagar_saude", "--atleta", "Atleta Que Nao Existe", esperado=1)
    saida = _worker(ctx, "apagar_saude", "--atleta", ATLETA)
    assert all(re.search(rf"saude {t}: apagadas=\d+", saida) for t in ("limiar", "zonas", "recordes", "carga")), saida
    for tabela in ("limiar_atleta", "zona_fc_atleta", "recorde_pessoal", "carga_garmin_dia"):
        assert _sql(ctx, f"select count(*) from {tabela} where atleta_id = 1") == [(0,)], tabela
    assert _sql(ctx, "select count(*) from atividade where atleta_id = 1") == n_ativ  # atleta e atividades ficam
    assert _sql(ctx, "select count(*) from atleta where nome = :n", n=ATLETA) == [(1,)]
    again = _worker(ctx, "apagar_saude", "--atleta", ATLETA)  # idempotente
    assert re.findall(r"apagadas=(\d+)", again) == ["0"] * 4
    # recalcular sem saude: nada de limiar estimado, tudo "sem_dados_saude" (menos natacao)
    _worker(ctx, "calcular_carga", "--atleta-id", "1")
    ids = _ids(ctx)
    for fonte, motivo in orc.SEM_SAUDE.items():
        c = _atividade(ctx, 1, ids[fonte])["carga"]
        assert (c["estado"], c["motivo"], c["carga"]) == ("sem_carga", motivo, None), fonte
    j = _serie(ctx, 1)
    assert j["dias"] == [] and j["aviso"] == "sem_carga_calculada"
    assert j["totais"]["por_motivo"] == orc.TOTAIS_SEM_SAUDE["por_motivo"]
    # reimportar a saude e recalcular volta ao oraculo
    _worker(ctx, "importar_saude", str(ZIP), "--atleta", ATLETA)
    _worker(ctx, "calcular_carga", "--atleta-id", "1")
    assert _serie(ctx, 1)["totais"]["calculadas"] == orc.TOTAIS["calculadas"]
    assert _perto(_atividade(ctx, 1, ids[4000000003])["carga"]["carga"], orc.ESPERADO[4000000003].carga)
