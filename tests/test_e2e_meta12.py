"""QA de ponta a ponta da Meta 12, o treino inteiro na tela do atleta (issue #469; #462 a #467 e #237).

Segue `docs/produto/meta-12-como-rodar.md`: migracoes (alembic, ate o head) -> as 81 atividades sinteticas da Meta 7
(`tests/fixtures/meta7/`) -> `GET` da atividade com os blocos que a tela le (`linha_base@3`, `carga`, `forma_do_dia`,
`transicao.editavel`) -> correcao do rotulo de transicao (`PUT`/`DELETE`, `409`) -> casos sinteticos escritos a mao
(piso da `@3` contra a `@2`, 7 e 8 amostras, `sem_carga` com motivo, sugestao contra correcao do atleta e reimportacao).
Um teste por item do criterio de pronto da meta (`docs/produto/roadmap.md`, Meta 12). O que o app faz com esses blocos
(um teste por estado de cada cartao) esta em `apps/mobile/__tests__/TelaTreino.test.tsx`; aqui o app so entra por varredura
do codigo-fonte (ele nao calcula) e pelo contrato.

Num SQLite temporario; so dado sintetico; sem rede (guarda de socket no processo e nos subprocessos). Os testes seguem a
ordem do arquivo e dividem o mesmo banco, entao a ordem importa.
"""

import json
import os
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
API = RAIZ / "services" / "api"
APP = RAIZ / "apps" / "mobile"
PASTA7 = RAIZ / "tests" / "fixtures" / "meta7"
FIT = RAIZ / "tests" / "fixtures" / "garmin" / "fit"
FIXTURES = json.loads((PASTA7 / "atividades.json").read_text(encoding="utf-8"))["atividades"]

if str(API) not in sys.path:
    sys.path.insert(0, str(API))

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


def _roda(args, env, cwd=RAIZ):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
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

    base = tmp_path_factory.mktemp("e2e_meta12")
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
    _roda(["-m", "alembic", "upgrade", "head"], env, API)
    eng = create_engine(url)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: base / "fit"
    try:
        yield {"client": TestClient(app), "eng": eng}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _get(ctx, atleta, atividade, status=200):
    r = ctx["client"].get(f"/atletas/{atleta}/atividades/{atividade}")
    assert r.status_code == status, (r.status_code, r.text[:300])
    return r.json()


def _put(ctx, atleta, atividade, valor, status=200):
    r = ctx["client"].put(f"/atletas/{atleta}/atividades/{atividade}/transicao", json={"transicao": valor})
    assert r.status_code == status, (r.status_code, r.text[:300])
    return r.json()


def _delete(ctx, atleta, atividade, status=200):
    r = ctx["client"].delete(f"/atletas/{atleta}/atividades/{atividade}/transicao")
    assert r.status_code == status, (r.status_code, r.text[:300])
    return r.json()


def _id(ctx, fonte_id, atleta=1):
    return _sql(ctx, "select id from atividade where atleta_id = :a and fonte_id = :f", a=atleta, f=fonte_id)[0][0]


def _metricas(j):
    return {m["chave"]: m for m in j["linha_base"]["metricas"]}


def _novo_atleta(ctx, nome):
    from app.db.models import Atleta

    with Session(ctx["eng"]) as s:
        a = Atleta(nome=nome)
        s.add(a)
        s.commit()
        return a.id


def _corridas_leves(ctx, atleta, paces, sessao_pace):
    """`paces` (s/km) viram corridas leves de 10 km, uma por semana; depois a sessao de `sessao_pace`. Devolve o id da sessao."""
    from app.db.models import Atividade

    base = datetime(2026, 1, 2, 7, tzinfo=UTC)
    with Session(ctx["eng"]) as s:
        for i, p in enumerate([*paces, sessao_pace]):
            a = Atividade(
                atleta_id=atleta, fonte="sintetico", fonte_id=f"s{i}", modalidade="corrida", subtipo=None,
                inicio=base + timedelta(days=7 * i), fuso_min=0, duracao_s=p * 10, distancia_m=10000, fc_media=145,
                tipo_treino="leve", tipo_origem="sugestao", tipo_confirmado=False)
            s.add(a)
        s.commit()
    return _sql(ctx, "select max(id) from atividade where atleta_id = :a", a=atleta)[0][0]


# ---------------------------------------------------------------- ambiente e carga (passos 2 e 3 do guia)

def test_01_migracoes_ate_o_head_e_carga_das_81_atividades(ctx):
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(API / "alembic.ini"))
    cfg.set_main_option("script_location", str(API / "alembic"))
    assert _sql(ctx, "select version_num from alembic_version") == [(ScriptDirectory.from_config(cfg).get_current_head(),)]
    assert len(FIXTURES) == 81
    assert _importa_fixtures(ctx["eng"]) == 1
    origens = dict(_sql(ctx, "select coalesce(tipo_origem,'(sem)'), count(*) from atividade group by 1"))
    assert origens == {"(sem)": 40, "professor": 1, "sugestao": 39, "trainingpeaks": 1}  # passo 3 do guia


# ---------------------------------------------------------------- critério: linha_base@3 (#462) na seção do normal (#465)

def test_02_o_get_traz_a_linha_de_base_na_3_com_texto_pronto(ctx):
    """Passo 5 do guia: a tela do normal le a `@3` e so mostra os textos prontos da API."""
    j = _get(ctx, 1, 81)
    lb = j["linha_base"]
    assert (lb["estado"], lb["versao"], lb["janela_semanas"], lb["minimo_treinos"]) == ("ok", "linha_base@3", 12, 8)
    m = _metricas(j)
    assert set(m) == {"melhor_pace", "fc_melhor_tiro", "fc_media", "carga_hora"}
    assert [m[c]["estado"] for c in ("melhor_pace", "fc_melhor_tiro", "fc_media", "carga_hora")] == ["fora", "dentro", "fora", "sem_valor"]
    assert m["melhor_pace"]["valor_texto"] == "5:00/km" and m["fc_media"]["valor_texto"] == "150 bpm"
    assert "39 s/km mais lento que a mediana de 4:21/km (11 treinos" in m["melhor_pace"]["texto"]
    assert "perto da mediana de 172 bpm" in m["fc_melhor_tiro"]["texto"]
    for c in ("melhor_pace", "fc_media"):  # "fora" leva a nota de que nao e julgamento
        assert m[c]["texto"].endswith("Isto compara com o seu histórico; não diz se o treino foi bom ou ruim.")
    assert m["carga_hora"]["texto"] == "Sem carga por hora neste treino: a carga ainda não foi calculada."
    assert "@2" not in json.dumps(j)  # o atleta nunca ve a regra antiga


def test_03_piso_da_3_tira_o_fora_so_pela_dispersao_pequena_e_a_2_continua_reproduzivel(ctx):
    """Exemplo da ADR 0011 (mediana 330, MAD 6): 306 s/km e `fora` na `@2` e `dentro` na `@3` (piso de 3% = 9,9)."""
    from app.metricas import linha_base as lb

    atleta = _novo_atleta(ctx, "Sintetico Piso")
    janela = [330, 324, 336, 330, 342, 318, 330, 336]
    sessao = _corridas_leves(ctx, atleta, janela, 306)
    pace = _metricas(_get(ctx, atleta, sessao))["pace_medio"]
    assert pace["estado"] == "dentro" and pace["n"] == 8  # a @3 pela API
    base = datetime(2026, 1, 2, 7, tzinfo=UTC)

    def treino(i, p):
        ini = base + timedelta(days=7 * i)
        return lb.Treino(id=i, inicio=ini, dia=ini.date(), modalidade="corrida", tipo_treino="leve", valores={"pace_medio": float(p)})

    hist = [treino(i, p) for i, p in enumerate(janela)]
    v2 = lb.linha_base(treino(8, 306), hist, lb.PARAMETROS_V2)
    assert (v2.versao, v2.metricas[0].estado) == ("linha_base@2", "fora")  # a @2 marcaria "fora" so pela dispersao
    assert lb.linha_base(treino(8, 306), hist).metricas[0].estado == "dentro"
    # um desvio grande continua fora na @3
    outro = _novo_atleta(ctx, "Sintetico Longe")
    longe = _corridas_leves(ctx, outro, janela, 280)
    assert _metricas(_get(ctx, outro, longe))["pace_medio"]["estado"] == "fora"


def test_04_minimo_de_8_amostras_do_mesmo_tipo(ctx):
    sete = _corridas_leves(ctx, _novo_atleta(ctx, "Sintetico Sete"), [330, 324, 336, 330, 342, 318, 330], 306)
    a7 = _sql(ctx, "select atleta_id from atividade where id = :i", i=sete)[0][0]
    m7 = _metricas(_get(ctx, a7, sete))["pace_medio"]
    assert (m7["estado"], m7["n"]) == ("aprendendo", 7)
    assert "7 de 8 treinos" in m7["texto"] and "mediana" not in m7["texto"]  # sem mediana enquanto aprende
    oito = _corridas_leves(ctx, _novo_atleta(ctx, "Sintetico Oito"), [330, 324, 336, 330, 342, 318, 330, 336], 306)
    a8 = _sql(ctx, "select atleta_id from atividade where id = :i", i=oito)[0][0]
    assert _metricas(_get(ctx, a8, oito))["pace_medio"]["n"] == 8


# ---------------------------------------------------------------- critério: carga e forma do dia em números (#466)

def test_05_carga_e_forma_do_dia_em_numeros_sem_arredondar_no_app(ctx):
    j = _get(ctx, 1, 78)  # ciclismo de 25/03, com carga (guia, passo 6)
    assert j["carga"]["estado"] == "calculada" and j["carga"]["carga"] == 45.0
    assert (j["carga"]["valor_texto"], j["carga"]["metodo_texto"], j["carga"]["texto"]) == ("45,0", "Estimada pela FC.", None)
    f = j["forma_do_dia"]
    assert (f["estado"], f["ctl_texto"], f["atl_texto"], f["tsb_texto"]) == ("calculada", "6,1", "10,0", "−3,9")  # U+2212
    assert f["data_local"] == j["data_local"] and f["sem_carga_no_dia"] == 0
    # sem grafico: o GET nao traz a serie, so o dia
    assert not {"serie", "pontos", "historico"} & set(f)


def test_06_forma_aprendendo_nao_traz_os_tres_numeros(ctx):
    j = _get(ctx, 1, 10)
    assert j["carga"]["valor_texto"] == "30,0"
    f = j["forma_do_dia"]
    assert f["estado"] == "aprendendo" and f["ctl_texto"] is f["atl_texto"] is f["tsb_texto"] is None
    assert f["texto_aprendendo"] == "Ainda aprendendo a sua forma: faltam 39 dias de histórico para estimar."


def test_07_carga_pendente_e_sem_carga_com_o_motivo_da_api(ctx):
    from app.db.models import Atividade, CargaAtividade
    from app.metricas import carga as cg
    from app.servicos import carga_textos as ct

    pendente = _get(ctx, 1, 81)  # fixtures da Meta 7 nao gravam carga no 81
    assert pendente["carga"]["estado"] == "pendente" and pendente["carga"]["texto"] == "A carga deste treino ainda não foi calculada."
    assert pendente["forma_do_dia"]["estado"] == "sem_serie"
    atleta = _novo_atleta(ctx, "Sintetico SemCarga")
    with Session(ctx["eng"]) as s:
        a = Atividade(atleta_id=atleta, fonte="sintetico", fonte_id="sc", modalidade="corrida", inicio=datetime(2026, 3, 1, 7, tzinfo=UTC),
                      fuso_min=0, duracao_s=3000, distancia_m=8000, fc_media=None)
        s.add(a)
        a.carga = CargaAtividade(estado="sem_carga", motivo="sem_fc", granularidade="atividade", entrada="y" * 64, versao=cg.VERSAO,
                                 calculado_em=datetime(2026, 4, 1, tzinfo=UTC))
        s.commit()
        aid = a.id
    c = _get(ctx, atleta, aid)["carga"]
    assert (c["estado"], c["motivo"], c["carga"], c["valor_texto"]) == ("sem_carga", "sem_fc", None, None)
    assert c["texto"] == ct.MOTIVO_TEXTO["sem_fc"] and c["texto"]  # o motivo e frase pronta da API


# ---------------------------------------------------------------- critério: esforços e distância/pace (#467, #237)

def test_08_esforcos_com_e_sem_esforco(ctx):
    com = _get(ctx, 1, 81)["esforcos"]
    assert com["versao"].startswith("esforcos@") and [b["categoria"] for b in com["blocos"]].count("esforco") == 6
    sem = _get(ctx, 1, _id(ctx, "2026-01-04/cor1"))["esforcos"]
    assert sem is None or all(b["categoria"] != "esforco" for b in sem["blocos"])


def test_09_distancia_e_pace_chegam_como_texto_pronto_e_a_tela_os_desenha_igual(ctx):
    """#237: a API manda o texto e a tela usa o mesmo componente de linha para as duas."""
    j = _get(ctx, 1, 81)
    assert (j["distancia"], j["pace_medio"], j["duracao"]) == ("15,00 km", "6:00", "1:30:00")
    fonte = (APP / "src" / "componentes" / "TelaTreino.tsx").read_text(encoding="utf-8")
    dist = re.search(r'<Linha [^>]*rotulo="Distância"[^>]*/>', fonte)
    pace = re.search(r'<Linha [^>]*rotulo="Pace médio"[^>]*/>', fonte)
    assert dist and pace and dist.group(0).startswith("<Linha styles={styles}") and pace.group(0).startswith("<Linha styles={styles}")


# ---------------------------------------------------------------- critério: rótulo de transição corrigido pelo atleta (#467)

def test_10_corrigir_a_transicao_muda_a_linha_de_base_e_desfazer_volta(ctx):
    antes = _get(ctx, 1, 81)
    assert antes["transicao"] == {"valor": False, "origem": None, "editavel": True}
    assert _put(ctx, 1, 81, True) == {"valor": True, "origem": "atleta", "editavel": True}
    depois = _get(ctx, 1, 81)
    assert depois["transicao"]["origem"] == "atleta"
    m = _metricas(depois)
    assert [m[c]["estado"] for c in ("melhor_pace", "fc_melhor_tiro", "fc_media")] == ["aprendendo"] * 3  # compara so com transicao
    assert _delete(ctx, 1, 81) == {"valor": False, "origem": None, "editavel": True}
    assert _get(ctx, 1, 81)["linha_base"] == antes["linha_base"]


def test_11_onde_a_api_nao_aceita_rotulo_editavel_e_falso_e_o_409_nao_grava(ctx):
    ids = [i for (i,) in _sql(ctx, "select id from atividade where atleta_id = 1 and modalidade not in ('corrida','natacao','ciclismo')")]
    assert ids  # as fixtures tem atividades `outra`
    antes = _sql(ctx, "select count(*) from rotulo_transicao")
    for i in ids[:3]:
        j = _get(ctx, 1, i)
        assert j["transicao"]["editavel"] is False and j["carga"] is None and j["forma_do_dia"] is None
        for chamada in (lambda: ctx["client"].put(f"/atletas/1/atividades/{i}/transicao", json={"transicao": True}),
                        lambda: ctx["client"].delete(f"/atletas/1/atividades/{i}/transicao")):
            r = chamada()
            assert (r.status_code, r.json()) == (409, {"detail": "Este treino não tem rótulo de transição."})
    assert _sql(ctx, "select count(*) from rotulo_transicao") == antes
    assert ctx["client"].put("/atletas/1/atividades/999999/transicao", json={"transicao": True}).status_code == 404


def test_12_a_correcao_do_atleta_vence_a_sugestao_e_a_reimportacao_nao_desfaz(ctx):
    """Decisao de 06/11 (ADR 0009): ciclismo + corrida coladas formam o par; o atleta diz "nao" e isso fica."""
    from app.db.models import Atividade
    from app.servicos.transicao import aplicar_sugestao

    atleta = _novo_atleta(ctx, "Sintetico Transicao")
    with Session(ctx["eng"]) as s:
        s.add_all([
            Atividade(atleta_id=atleta, fonte="sintetico", fonte_id="bike", modalidade="ciclismo", inicio=datetime(2026, 3, 10, 8, tzinfo=UTC),
                      fuso_min=0, duracao_s=3600, distancia_m=30000),
            Atividade(atleta_id=atleta, fonte="sintetico", fonte_id="run", modalidade="corrida", inicio=datetime(2026, 3, 10, 9, 5, tzinfo=UTC),
                      fuso_min=0, duracao_s=1800, distancia_m=5000),
        ])
        s.commit()
        assert aplicar_sugestao(s, atleta).inseridas == 2
    corrida = _id(ctx, "run", atleta)
    assert _get(ctx, atleta, corrida)["transicao"] == {"valor": True, "origem": "sugerido", "editavel": True}
    assert _put(ctx, atleta, corrida, False) == {"valor": False, "origem": "atleta", "editavel": True}
    with Session(ctx["eng"]) as s:
        aplicar_sugestao(s, atleta)  # a rodada de sugestao nao toca na correcao
    # importacao de verdade: um FIT novo dispara a sugestao do atleta inteiro
    fit = (FIT / "upload_rodagem_6km.fit").read_bytes()
    r = ctx["client"].post(f"/atletas/{atleta}/atividades/fit", files={"arquivo": ("t.fit", fit, "application/octet-stream")})
    assert r.status_code == 201, r.text[:300]
    r = ctx["client"].post(f"/atletas/{atleta}/atividades/fit", files={"arquivo": ("t.fit", fit, "application/octet-stream")})
    assert r.status_code == 200  # reenvio
    assert _get(ctx, atleta, corrida)["transicao"] == {"valor": False, "origem": "atleta", "editavel": True}
    # a outra parte do par segue sugerida; "voltar a sugestao" (DELETE) devolve o sim da regra
    assert _get(ctx, atleta, _id(ctx, "bike", atleta))["transicao"]["origem"] == "sugerido"
    assert _delete(ctx, atleta, corrida) == {"valor": True, "origem": "sugerido", "editavel": True}


# ---------------------------------------------------------------- critério: o app não calcula; contrato e fixtures do app

def test_13_ler_nao_grava_nada(ctx):
    tabelas = ("atividade", "carga_atividade", "rotulo_transicao", "bloco_atividade")
    antes = [_sql(ctx, f"select count(*) from {t}") for t in tabelas]
    for i in (1, 10, 78, 81):
        _get(ctx, 1, i)
    assert [_sql(ctx, f"select count(*) from {t}") for t in tabelas] == antes


def test_14_o_app_nao_calcula_so_mostra_o_que_o_get_devolve():
    """Varredura do codigo dos cartoes: nada de arredondar, somar, mediana nem grafico; o contrato do cliente tem os campos."""
    proibidos = re.compile(r"toFixed|Math\.|\.reduce\(|toLocale|Intl\.|mediana\(|parseFloat|Number\(")
    for nome in ("TelaTreino", "CartaoNormal", "CartaoCargaForma", "CartaoEsforcos", "CartaoTransicao"):
        fonte = (APP / "src" / "componentes" / f"{nome}.tsx").read_text(encoding="utf-8")
        assert not proibidos.search(fonte), (nome, proibidos.search(fonte).group(0))
    carga = (APP / "src" / "componentes" / "CartaoCargaForma.tsx").read_text(encoding="utf-8")
    assert "<GraficoTiros" not in carga and "react-native-svg" not in carga  # sem grafico da serie
    assert "ctl_texto" in carga and "atl_texto" in carga and "tsb_texto" in carga
    cliente = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "packages" / "api-client").rglob("*.ts") if "node_modules" not in p.parts)
    for campo in ("forma_do_dia", "valor_texto", "metodo_texto", "editavel", "texto_aprendendo"):
        assert campo in cliente, campo


def test_15_fixtures_e_api_falsa_do_app_nao_tem_mais_a_regra_antiga():
    for caminho in [*(APP / "__fixtures__").rglob("*"), APP / "scripts" / "api-falsa.mjs"]:
        if caminho.is_file():
            assert "linha_base@2" not in caminho.read_text(encoding="utf-8"), caminho


def test_16_spec_e_guia_existem_com_as_secoes_da_meta():
    spec = (RAIZ / "docs" / "design" / "telas" / "treino.md").read_text(encoding="utf-8")
    for secao in ("Comparado com o seu normal", "Carga e forma do dia", "Esforços", "Treino de transição", "#237"):
        assert secao in spec, secao
    guia = (RAIZ / "docs" / "produto" / "meta-12-como-rodar.md").read_text(encoding="utf-8")
    assert "treino-meta12" in guia and "5433" in guia  # guia com projeto proprio e o aviso do banco real
