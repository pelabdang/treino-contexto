"""QA de ponta a ponta da Meta 8, o check-in pós-treino e a carga pela PSE (issue #301, ADR 0012).

Segue o roteiro de `docs/produto/meta-8-como-rodar.md`: migrações (alembic, até a 0012) -> as 18 atividades sintéticas de
`tests/fixtures/meta8/` e o check-in de 15/10 gravados no banco (como o `carregar.py` do guia, com o mesmo deslocamento de datas
para "hoje") -> API (TestClient): os oito `PUT` do passo 5, os `422`, `GET`/edição/`DELETE`/`404`, o `GET` da atividade com
`checkin`, `checkin_aberto`, `pse_sugerida` e `carga_pse@1` contra o oráculo `CARGA_PSE_ESPERADA`, a lista de pendentes contra
`PENDENTES` -> a validação do corpo contra `VALIDACAO` -> `worker.apagar_checkin` em subprocesso -> OpenAPI e cliente.
Num SQLite temporário; só dado sintético. Sem rede: os subprocessos rodam com uma guarda de socket (`sitecustomize`) e o teste
tem a mesma guarda. O check-in é dado de saúde: o teste confere que o texto marcador nunca volta num `422` nem vai para o log.

Os testes seguem a ordem do arquivo e dividem o mesmo banco (como os e2e das Metas 2 a 7), então a ordem importa.
"""

import importlib.util
import json
import logging
import os
import socket
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "tests" / "fixtures" / "meta8"
API = RAIZ / "services" / "api"
MARCADOR = "MARCADOR-SINTETICO-123"
FORA_DO_PRAZO = "2026-10-15/cor1"

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


O = _carregar("oraculo_meta8_e2e", PASTA / "oraculo.py")
FIXTURES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
CHECKINS = json.loads((PASTA / "checkins.json").read_text(encoding="utf-8"))

# PSE sugerida (parte anterior do multiesporte): fonte_id -> (pse_sugerida, pse do próprio check-in)
SUGESTAO = {"2026-11-03/nat1": None, "2026-11-03/cic1": 5, "2026-11-03/cor1": 6}


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


def _carrega_fixtures(eng):
    """O passo 3 do guia: 18 atividades e um check-in (o de 15/10, fora do prazo de criação). Devolve (atleta, deslocamento)."""
    from app.db.models import Atividade, Atleta, CheckinTreino
    from app.servicos.checkin import hoje_local

    desloc = (hoje_local() - date(2026, 11, 9)).days  # as fixtures valem para "hoje = 09/11/2026"
    agora = datetime.now(UTC)
    with Session(eng) as s:
        atleta = Atleta(nome="Atleta Fictício")
        s.add(atleta)
        s.flush()
        for f in FIXTURES:
            a = Atividade(
                atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
                inicio=datetime.fromisoformat(f["inicio"]) + timedelta(days=desloc), fuso_min=f["fuso_min"],
                duracao_s=f["duracao_s"])
            s.add(a)
            s.flush()
            c = CHECKINS.get(f["id"])
            if c and f["id"] == FORA_DO_PRAZO:
                s.add(CheckinTreino(
                    atividade_id=a.id, pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"],
                    texto=c["texto"], versao="checkin@1", registrado_em=agora, atualizado_em=agora,
                    **{k: k in c["atalhos"] for k in ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")}))
        s.commit()
        return atleta.id, desloc


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.session import get_session
    from app.main import app

    base = tmp_path_factory.mktemp("e2e_meta8")
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
    try:
        yield {"client": TestClient(app), "eng": eng, "env": env, "app": app, "saidas": []}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _ids(ctx):
    """fonte_id (ex.: '2026-11-05/cor1') -> id da atividade no banco."""
    return {f: i for i, f in _sql(ctx, "select id, fonte_id from atividade where atleta_id = 1")}


def _fonte(ctx):
    return {i: f for f, i in _ids(ctx).items()}


def _rota(ctx, f, sufixo=""):
    return f"/atletas/1/atividades/{_ids(ctx)[f]}{sufixo}"


def _put(ctx, f, corpo, status=200, atleta=1):
    r = ctx["client"].put(f"/atletas/{atleta}/atividades/{_ids(ctx)[f]}/checkin", json=corpo)
    assert r.status_code == status, (f, r.status_code, r.text[:300])
    return r


def _get(ctx, caminho, status=200):
    r = ctx["client"].get(caminho)
    assert r.status_code == status, (caminho, r.status_code, r.text[:300])
    return r.json()


def _n_checkins(ctx):
    return _sql(ctx, "select count(*) from checkin_treino")[0][0]


def _worker(ctx, *args, esperado=0):
    r = _roda(["-m", "worker.apagar_checkin", *args], ctx["env"], esperado=esperado)
    ctx["saidas"].append(r.stdout + r.stderr)
    return r.stdout + r.stderr


# ---------------------------------------------------------------- migração e carga (passos 2 e 3)

def test_01_migracao_0012_cria_checkin_treino_um_por_atividade(ctx):
    assert _sql(ctx, "select version_num from alembic_version") == [("0013",)]
    colunas = {c[1] for c in _sql(ctx, "pragma table_info(checkin_treino)")}
    assert {"atividade_id", "pse", "sensacao", "nada_a_relatar", "texto", "versao", "registrado_em", "atualizado_em",
            "dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse"} <= colunas
    unicos = [r for r in _sql(ctx, "pragma index_list(checkin_treino)") if r[2]]  # índice único por atividade
    assert unicos, "checkin_treino precisa de um índice único por atividade (uma atividade nunca tem dois check-ins)"


def test_02_carga_das_18_atividades_e_do_checkin_de_15_10(ctx):
    assert len(FIXTURES) == 18
    atleta, desloc = _carrega_fixtures(ctx["eng"])
    ctx["desloc"] = desloc
    print(f"deslocamento {desloc} dias (data do teste: {datetime.now().astimezone():%d/%m/%Y %H:%M})")
    assert atleta == 1
    assert _sql(ctx, "select count(*) from atividade") == [(18,)]
    assert _n_checkins(ctx) == 1
    assert _ids(ctx)["2026-10-15/cor1"] == 1  # a tabela de ids do guia: na ordem do arquivo
    assert _ids(ctx)["2026-11-05/cor1"] == 12 and _ids(ctx)["2026-11-09/cor2"] == 18


# ---------------------------------------------------------------- PUT, 422, GET, DELETE (passos 5 a 7)

def test_03_os_oito_put_do_passo_5_dao_200_nas_atividades_do_guia(ctx):
    ids = []
    for f, corpo in CHECKINS.items():
        if f == FORA_DO_PRAZO:
            continue
        r = _put(ctx, f, corpo)
        assert r.json()["versao"] == "checkin@1" and r.json()["pse"] == corpo["pse"]
        ids.append(_ids(ctx)[f])
    assert ids == [17, 18, 15, 16, 14, 13, 6, 8]
    assert _n_checkins(ctx) == 9


def test_04_422_de_prazo_e_de_multiesporte_com_a_data_local(ctx):
    corpo = {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": []}
    for f in ("2026-11-01/cor1", "2026-11-01/cor2"):  # a cor2 as 23:30 local: ja e 02/11 em UTC, vale a data local
        d = _put(ctx, f, corpo, 422).json()["detail"]
        assert d == [{"loc": ["path", "atividade_id"], "msg": "o check-in só pode ser criado até 7 dias depois do treino",
                      "type": "fora_do_prazo"}]
    for f in ("2026-11-03/out1", "2026-11-03/out2", "2026-11-03/out3"):
        d = _put(ctx, f, corpo, 422).json()["detail"]
        assert d == [{"loc": ["path", "atividade_id"], "msg": "esta parte do treino multiesporte não pede check-in",
                      "type": "atividade_sem_checkin"}]
    for f in ("2026-11-02/cor1", "2026-11-03/cor1", "2026-11-04/cic1"):  # dentro do prazo, ate o limite (02/11, fuso nulo)
        assert O.PRAZO_CRIAR[f] is True
    assert O.PRAZO_CRIAR["2026-11-01/cor1"] is False and O.PRAZO_CRIAR["2026-11-01/cor2"] is False
    assert _n_checkins(ctx) == 9  # nenhum 422 gravou nada


def test_05_422_do_corpo_nunca_repete_a_entrada(ctx, caplog):
    caplog.set_level(logging.DEBUG)
    r = _put(ctx, "2026-11-05/cor1", {"pse": 11, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": MARCADOR}, 422)
    d = r.json()["detail"]
    assert d[0]["loc"] == ["body", "pse"] and d[0]["type"] == "less_than_equal"
    assert "input" not in d[0] and MARCADOR not in r.text
    r = _put(ctx, "2026-11-05/cor1", {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": ["dor"], "texto": MARCADOR}, 422)
    d = r.json()["detail"]
    assert d == [{"loc": ["body"], "msg": "Value error, nada a relatar não combina com atalho nem texto", "type": "value_error"}]
    assert MARCADOR not in r.text
    assert MARCADOR not in caplog.text  # dado de saude: nunca em log
    assert _n_checkins(ctx) == 9


def test_06_get_edicao_substitui_tudo_e_delete_idempotente(ctx):
    u = _rota(ctx, "2026-11-05/cor1", "/checkin")
    assert _get(ctx, u, 404) == {"detail": "sem check-in"}
    h = {"content-type": "application/json"}
    c = ctx["client"]
    j = c.put(u, json={"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["dor", "sono_ruim"], "texto": None}, headers=h).json()
    assert (j["pse"], j["pse_texto"], j["sensacao_texto"], j["versao"]) == (5, "difícil", "normal", "checkin@1")
    assert [a["texto"] for a in j["atalhos"]] == ["Dor", "Sono ruim"]
    assert j["registrado_em"] == j["atualizado_em"] and j["registrado_em"].endswith("-03:00")
    j2 = c.put(u, json={"pse": 8, "sensacao": 2, "nada_a_relatar": False, "atalhos": ["calor"], "texto": "  Dia quente.  "}, headers=h).json()
    assert (j2["pse"], j2["pse_texto"], j2["sensacao_texto"], j2["texto"]) == (8, "8", "mal", "Dia quente.")  # o 8 nao tem ancora
    assert [a["chave"] for a in j2["atalhos"]] == ["calor"]  # os atalhos antigos saem
    assert j2["registrado_em"] == j["registrado_em"] and j2["atualizado_em"] > j["atualizado_em"]
    assert _n_checkins(ctx) == 10  # editar nao cria um segundo
    assert c.delete(u).status_code == 204
    assert c.delete(u).status_code == 204  # idempotente
    assert _get(ctx, u, 404) == {"detail": "sem check-in"}
    assert _n_checkins(ctx) == 9


def test_07_outro_atleta_e_atleta_inexistente_dao_404(ctx):
    c = ctx["client"]
    assert c.delete("/atletas/2/atividades/12/checkin").json() == {"detail": "atleta não encontrado"}
    assert c.get("/atletas/2/atividades/12/checkin").status_code == 404
    _put(ctx, "2026-11-05/cor1", CHECKINS["2026-11-09/cor1"], 404, atleta=2)
    assert _n_checkins(ctx) == 9
    _get(ctx, "/atletas/1/checkins/pendentes?dias=8", 422)
    _get(ctx, "/atletas/1/checkins/pendentes?dias=0", 422)


def test_08_validacao_do_corpo_bate_com_o_oraculo(ctx):
    alvo = "2026-11-05/cor1"  # sem check-in; cada corpo valido vira check-in e e apagado em seguida
    for desc, corpo, valido, motivo in O.VALIDACAO:
        r = ctx["client"].put(_rota(ctx, alvo, "/checkin"), json=corpo)
        assert r.status_code == (200 if valido else 422), (desc, r.status_code, r.text[:200])
        assert "input" not in r.text
        if valido:
            assert ctx["client"].delete(_rota(ctx, alvo, "/checkin")).status_code == 204
    assert _n_checkins(ctx) == 9


# ---------------------------------------------------------------- carga pela PSE e GET da atividade (passo 8)

def test_09_carga_pse_e_campos_da_atividade_batem_com_o_oraculo(ctx):
    for f, i in _ids(ctx).items():
        d = _get(ctx, f"/atletas/1/atividades/{i}")
        esperado = O.CARGA_PSE_ESPERADA[f]
        c = d["carga_pse"]
        if esperado is None:  # pai e trocas
            assert c is None and d["checkin"] is None and d["checkin_aberto"] is False, f
            continue
        estado, _minutos, valor = esperado
        assert c["estado"] == estado, f
        assert c["valor"] == (pytest.approx(valor) if valor is not None else None), f
        assert (d["checkin"] is not None) == (estado in ("calculada", "sem_duracao")), f
        assert d["pse_sugerida"] == SUGESTAO.get(f), f
        assert d["checkin_aberto"] is (f not in ("2026-11-01/cor1", "2026-11-01/cor2")), f  # as de 01/11 ja passaram do prazo


def test_10_textos_da_carga_pse_e_da_natacao(ctx):
    def carga(f):
        return _get(ctx, _rota(ctx, f))["carga_pse"]

    assert carga("2026-11-09/cor2")["texto"] == "Carga pela PSE: 6 x 45 min = 270 UA." and carga("2026-11-09/cor2")["valor_texto"] == "270 UA"
    d = carga("2026-11-07/cor1")
    assert (d["valor"], d["valor_texto"], d["texto"]) == (272.5, "272,5 UA", "Carga pela PSE: 6 x 45 min 25 s = 272,5 UA.")
    assert carga("2026-11-06/out1")["valor_texto"] == "0 UA"  # PSE 0 vale
    assert carga("2026-11-05/cor1")["texto"] == "Sem check-in: a carga pela PSE precisa da PSE do treino."
    assert carga("2026-11-09/cor1")["texto"] == "Treino sem duração registrada: sem carga pela PSE."
    nat = _get(ctx, _rota(ctx, "2026-11-08/nat1"))
    assert nat["carga_pse"]["valor"] == 160.0  # a natacao tem carga pela PSE, mesmo sem carga@2
    assert nat["carga"]["estado"] != "calculada"  # aqui sem carga@2 gravada: a carga pela PSE nao depende dela, nem a soma
    cor = _get(ctx, _rota(ctx, "2026-11-09/cor2"))
    assert cor["carga_pse"]["valor"] == 270.0 and cor["carga"]["estado"] != "calculada"  # separada da carga@2


def test_11_pendentes_batem_com_o_oraculo_e_nao_trazem_o_checkin(ctx):
    p = _get(ctx, "/atletas/1/checkins/pendentes")
    fonte = _fonte(ctx)
    esperado = O.PENDENTES[("2026-11-09T15:00:00-03:00", 7)]
    assert [fonte[x["atividade_id"]] for x in p["pendentes"]] == esperado
    assert (p["dias"], p["total"]) == (7, 4)
    assert [x["atividade_id"] for x in p["pendentes"]] == [12, 11, 10, 4]
    assert set(p["pendentes"][0]) == {"atividade_id", "modalidade", "data_local", "hora_local", "duracao", "titulo"}
    assert p["pendentes"][0]["titulo"] == "Corrida, 45 min"
    assert [x["atividade_id"] for x in _get(ctx, "/atletas/1/checkins/pendentes?dias=5")["pendentes"]] == [12, 11]
    assert _get(ctx, "/atletas/1/checkins/pendentes?dias=3")["total"] == 0
    assert _get(ctx, "/atletas/1/checkins/pendentes?dias=1")["pendentes"] == []


def test_12_criar_na_atividade_do_limite_do_prazo_e_sair_dos_pendentes(ctx):
    _put(ctx, "2026-11-02/cor1", CHECKINS["2026-11-09/cor1"])  # 02/11 = hoje - 7, fuso nulo: dentro
    assert [x["atividade_id"] for x in _get(ctx, "/atletas/1/checkins/pendentes")["pendentes"]] == [12, 11, 10]
    assert ctx["client"].delete(_rota(ctx, "2026-11-02/cor1", "/checkin")).status_code == 204
    assert _get(ctx, "/atletas/1/checkins/pendentes")["total"] == 4


# ---------------------------------------------------------------- worker.apagar_checkin (passo 13)

def test_13_worker_apaga_so_os_checkins_e_e_idempotente(ctx):
    assert _n_checkins(ctx) == 9
    assert "checkins: apagados=9" in _worker(ctx, "--atleta", "Atleta Fictício")
    assert "checkins: apagados=0" in _worker(ctx, "--atleta", "Atleta Fictício")
    assert "atleta nao encontrado" in _worker(ctx, "--atleta", "Ninguém", esperado=1)
    assert _sql(ctx, "select (select count(*) from checkin_treino), (select count(*) from atividade), (select count(*) from atleta)") == [(0, 18, 1)]
    p = _get(ctx, "/atletas/1/checkins/pendentes")
    assert p["total"] == 12 and 12 in [x["atividade_id"] for x in p["pendentes"]]


def test_14_a_saida_do_worker_so_tem_contagens(ctx):
    for s in ctx["saidas"]:
        assert MARCADOR not in s and "Semana puxada" not in s and "Incômodo" not in s
        assert "conexao de rede" not in s


# ---------------------------------------------------------------- contrato

def test_15_openapi_declara_as_rotas_de_checkin_e_o_cliente_esta_regerado(ctx):
    spec = ctx["app"].openapi()
    rota = spec["paths"]["/atletas/{atleta_id}/atividades/{atividade_id}/checkin"]
    assert {"get", "put", "delete"} <= set(rota)
    assert "get" in spec["paths"]["/atletas/{atleta_id}/checkins/pendentes"]
    gravado = json.loads((RAIZ / "packages" / "api-client" / "openapi.json").read_text(encoding="utf-8"))
    assert gravado["paths"]["/atletas/{atleta_id}/atividades/{atividade_id}/checkin"] == rota
    schema_ts = (RAIZ / "packages" / "api-client" / "src" / "schema.d.ts").read_text(encoding="utf-8")
    assert "checkin_aberto" in schema_ts and "pse_sugerida" in schema_ts and "carga_pse" in schema_ts
