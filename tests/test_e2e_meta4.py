"""QA de ponta a ponta da Meta 4, o clima da atividade (issue #116, ADR 0007).

Migracoes (alembic) -> importacao das fixtures da Meta 1 e de `tests/fixtures/clima/` (funcao `importar`, sem rede)
-> upload de um FIT de clima pela API (TestClient, `FIT_DIR` em tmp_path) -> `preencher_posicoes` e `preencher_clima`
com o `ClienteOpenMeteo` real sobre `httpx.MockTransport` que devolve a resposta gravada -> `GET` da atividade
conferido contra o `oraculo_clima.json` em cada estado. Num SQLite temporario; so dado sintetico (Parque do Exemplo).

Nao usamos `worker.importar_garmin`: no fim ele busca o clima com a rede de verdade. Uma guarda de socket derruba
qualquer conexao que nao seja local. Os testes seguem a ordem do arquivo e dividem o mesmo banco (como os e2e das
Metas 2 e 3), entao a ordem importa.
"""

import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
CLIMA = RAIZ / "tests" / "fixtures" / "clima"
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
ORACULO = json.loads((CLIMA / "oraculo_clima.json").read_text())
CASOS = {c["id"]: c for c in ORACULO["casos"]}
TOL = ORACULO["tolerancia_abs"]
RESPOSTAS = {
    "ok": (CLIMA / ORACULO["respostas"]["normal"]).read_bytes(),
    "null": (CLIMA / ORACULO["respostas"]["com_null"]).read_bytes(),
}
CHAVES_CLIMA = {"temperatura_c", "sensacao_c", "umidade_pct", "vento_kmh"}
OK = ["json_corrida_ar_livre", "fit_corrida_ar_livre", "fit_posicao_na_lap", "fit_corrida_longa_4_horas"]
CALCULADOS = ["fit_esteira_com_posicao", "json_esteira_com_posicao", "json_pedal_virtual_com_posicao",
              "fit_posicao_zero", "json_posicao_zero", "fit_posicao_invalida", "json_sem_coordenada"]


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local (a mesma guarda da #113): o Open-Meteo nunca e chamado."""
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def _host(endereco):
        return endereco[0] if isinstance(endereco, tuple) else endereco

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


def _roda(args, env, cwd):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r.stdout


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.clima import ClienteOpenMeteo
    from app.db.models import Atleta
    from app.db.session import get_session
    from app.ingestao.importacao import importar
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    base = tmp_path_factory.mktemp("e2e_meta4")
    url = f"sqlite:///{base / 'treino.db'}"
    fit_dir = base / "fit"
    env = {**os.environ, "DATABASE_URL": url}
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    eng = create_engine(url)
    estado = {"modo": "ok", "pedidos": []}

    def resposta(request: httpx.Request) -> httpx.Response:
        estado["pedidos"].append(request)
        modo = estado["modo"]
        if modo in RESPOSTAS:
            return httpx.Response(200, content=RESPOSTAS[modo], headers={"content-type": "application/json"})
        return httpx.Response(int(modo), json={"error": True, "reason": "simulado"})

    with Session(eng) as s:  # importar (e nao worker.importar_garmin): sem busca de clima, sem rede
        r1 = importar(s, ZIP, "Atleta Ficticio")
        r2 = importar(s, CLIMA / "exportacao_clima.json", "Atleta Ficticio")
        r3 = importar(s, CLIMA / "fit", "Atleta dos FIT")
        a1, a2 = s.scalars(select(Atleta).order_by(Atleta.id)).all()
        ids = (a1.id, a2.id)
    assert (r1.inseridas, r2.inseridas, r3.inseridas) == (5, 5, 6)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: fit_dir
    cliente = ClienteOpenMeteo(transporte=httpx.MockTransport(resposta), dormir=lambda s: None)
    try:
        yield {"client": TestClient(app), "eng": eng, "fit_dir": fit_dir, "atleta": ids[0], "atleta_fit": ids[1],
               "cliente": cliente, "estado": estado}
    finally:
        app.dependency_overrides.clear()
        cliente.fechar()
        eng.dispose()


# ---------------------------------------------------------------- ajudas
def _modo(ctx, modo):
    ctx["estado"]["modo"] = modo
    ctx["estado"]["pedidos"].clear()


def _chamadas(ctx):
    return len(ctx["estado"]["pedidos"])


def _rodar(ctx, **kw):
    """Uma rodada do comando (`worker.preencher_clima.rodar`) com o cliente real sobre o transporte falso."""
    from worker.preencher_clima import rodar

    with Session(ctx["eng"]) as s:
        _, estados, rel = rodar(s, ctx["cliente"], fit_dir=ctx["fit_dir"], pausa_s=0, **kw)
    return estados, rel


def _atividade(ctx, caso_id):
    """(atleta_id, atividade_id) do caso do oraculo."""
    from app.db.models import Atividade

    caso = CASOS[caso_id]
    arq = caso["arquivo"]
    inicio = datetime.fromisoformat(caso["inicio_utc"].replace("Z", "+00:00"))
    with Session(ctx["eng"]) as s:
        if "#" in arq:
            a = s.scalars(select(Atividade).where(Atividade.fonte == "garmin_export",
                                                  Atividade.fonte_id == arq.split("#")[1])).one()
        else:
            todas = s.scalars(select(Atividade).where(Atividade.atleta_id == ctx["atleta_fit"])).all()
            a = next(x for x in todas if x.inicio.replace(tzinfo=timezone.utc) == inicio)
        return a.atleta_id, a.id


def _get(ctx, atleta_id, atividade_id):
    r = ctx["client"].get(f"/atletas/{atleta_id}/atividades/{atividade_id}")
    assert r.status_code == 200
    return r.json()


def _confere(ctx, caso_id, estado=None):
    caso = CASOS[caso_id]
    esperado = estado or caso["estado"]
    j = _get(ctx, *_atividade(ctx, caso_id))
    assert j["clima"]["estado"] == esperado
    if esperado == "ok":
        assert set(j["clima"]) == {"estado", "atribuicao", *CHAVES_CLIMA}
        for k, v in caso["clima"].items():
            assert j["clima"][k] == pytest.approx(v, abs=TOL), (caso_id, k)
    else:
        assert j["clima"] == {"estado": esperado}  # fora do ok so o estado
    return j


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


# ---------------------------------------------------------------- 1. importacao, upload e posicao
def test_1_importacao_deixa_posicao_so_onde_o_oraculo_manda(ctx):
    _modo(ctx, "ok")
    esperado = ORACULO["posicao_guardada_esperada"]
    for caso_id in OK:
        lat, lon = _sql(ctx, "select inicio_lat, inicio_lon from atividade where id=:i",
                        i=_atividade(ctx, caso_id)[1])[0]
        assert (lat, lon) == (esperado["lat"], esperado["lon"]), caso_id  # 2 casas, nunca a exata
    for caso_id in CALCULADOS:
        pos = _sql(ctx, "select inicio_lat, inicio_lon from atividade where id=:i", i=_atividade(ctx, caso_id)[1])[0]
        assert tuple(pos) == (None, None), caso_id
    assert _chamadas(ctx) == 0


def test_2_upload_de_fit_de_clima_guarda_so_o_inicio(ctx):
    conteudo = (CLIMA / "fit" / "corrida_posicao_na_lap.fit").read_bytes()
    r = ctx["client"].post(f"/atletas/{ctx['atleta']}/atividades/fit",
                           files={"arquivo": ("treino.fit", conteudo, "application/octet-stream")})
    assert r.status_code == 201 and r.json()["resultado"] == "inserida"
    ctx["upload_id"] = r.json()["atividade_id"]
    lat, lon = _sql(ctx, "select inicio_lat, inicio_lon from atividade where id=:i", i=ctx["upload_id"])[0]
    assert (lat, lon) == (12.35, -45.68)
    assert len(list(ctx["fit_dir"].rglob("*.fit"))) == 1
    assert _chamadas(ctx) == 0


def test_3_posicao_do_passado_relida_sem_rede(ctx):
    from app.servicos.clima import preencher_posicoes

    id_json = _atividade(ctx, "json_corrida_ar_livre")[1]
    _sql(ctx, "update atividade set inicio_lat=null, inicio_lon=null where id=:i", i=id_json)
    _sql(ctx, "update atividade set inicio_lat=null, inicio_lon=null where id=:i", i=ctx["upload_id"])
    export = CLIMA / "exportacao_clima.json"
    with Session(ctx["eng"]) as s:
        # sem exportacao: so o FIT guardado no upload volta; o da exportacao fica sem posicao
        assert preencher_posicoes(s, fit_dir=ctx["fit_dir"]) == 1
        assert preencher_posicoes(s, exportacao=export, fit_dir=ctx["fit_dir"]) == 1
        assert preencher_posicoes(s, exportacao=export, fit_dir=ctx["fit_dir"]) == 0  # idempotente
    for i in (id_json, ctx["upload_id"]):
        assert _sql(ctx, "select inicio_lat, inicio_lon from atividade where id=:i", i=i)[0] == (12.35, -45.68)
    assert _chamadas(ctx) == 0


# ---------------------------------------------------------------- 2. clima ok, indoor, sem_posicao
def test_4_estados_antes_do_clima(ctx):
    # indoor e sem_posicao sao calculados; as de ar livre com posicao ainda nao foram consultadas
    for caso_id in CALCULADOS:
        _confere(ctx, caso_id)
    for caso_id in OK:
        _confere(ctx, caso_id, estado="pendente")


def test_5_clima_ok_confere_com_o_oraculo(ctx):
    _modo(ctx, "ok")
    estados, rel = _rodar(ctx)
    # as 4 do oraculo + o upload do mesmo FIT da lap (outro atleta): 5 atividades consultadas
    assert rel.chamadas == 5 and _chamadas(ctx) == 5
    assert estados["ok"] == 5 and estados["pendente"] == 0 and estados["falha"] == 0
    for caso_id in OK + CALCULADOS:
        _confere(ctx, caso_id)
    j = _get(ctx, ctx["atleta"], ctx["upload_id"])
    for k, v in CASOS["fit_posicao_na_lap"]["clima"].items():
        assert j["clima"][k] == pytest.approx(v, abs=TOL)


def test_6_idempotencia_segunda_rodada_nao_chama_nada(ctx):
    _modo(ctx, "ok")
    consulta = "select atividade_id, estado, consultado_em, tentativas from clima_atividade order by 1"
    antes = _sql(ctx, consulta)
    estados, rel = _rodar(ctx)
    assert rel.chamadas == 0 and _chamadas(ctx) == 0
    assert _sql(ctx, consulta) == antes
    assert estados["ok"] == 5


# ---------------------------------------------------------------- 3. pendente, falha
def test_7_pendente_dentro_dos_7_dias_nao_consulta(ctx):
    id_ = _atividade(ctx, "json_corrida_ar_livre")[1]
    original = _sql(ctx, "select inicio from atividade where id=:i", i=id_)[0][0]
    recente = (datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None)
    _sql(ctx, "update atividade set inicio=:r where id=:i", r=recente, i=id_)
    _modo(ctx, "ok")
    _, rel = _rodar(ctx)
    assert rel.chamadas == 0 and _chamadas(ctx) == 0  # nem chama, nem conta rodada
    _confere(ctx, "json_corrida_ar_livre", estado="pendente")
    _sql(ctx, "update atividade set inicio=:o where id=:i", o=original, i=id_)
    _confere(ctx, "json_corrida_ar_livre")  # a linha ok volta a valer (mesma entrada)
    assert _chamadas(ctx) == 0


def test_8_pendente_com_resposta_null_na_janela(ctx):
    _sql(ctx, "delete from clima_atividade")
    _modo(ctx, "null")
    estados, rel = _rodar(ctx)
    assert rel.chamadas == 5
    for caso_id in OK:  # o oraculo diz quem fica pendente: so a longa (13h a 16h) escapa dos null de 10h e 11h
        _confere(ctx, caso_id, estado=CASOS[caso_id]["estado_com_resposta_null"])
    pendentes = _sql(ctx, "select tentativas, erro from clima_atividade where estado='pendente'")
    assert len(pendentes) == 4 and all(t == 1 and "null" in e for t, e in pendentes)
    assert estados["ok"] == 1 and estados["pendente"] == 4


def test_9_pendente_vira_ok_na_rodada_seguinte(ctx):
    _modo(ctx, "ok")
    estados, rel = _rodar(ctx)
    assert rel.chamadas == 4 and estados["ok"] == 5 and estados["pendente"] == 0
    for caso_id in OK:
        _confere(ctx, caso_id)


def test_10_falha_http_400_na_hora_e_refazer_falhas(ctx):
    _sql(ctx, "delete from clima_atividade")
    _modo(ctx, "400")
    estados, rel = _rodar(ctx)
    assert rel.chamadas == 5 and estados["falha"] == 5 and estados["ok"] == 0
    assert _sql(ctx, "select distinct tentativas, erro from clima_atividade") == [(1, "HTTP 400")]
    for caso_id in OK:
        _confere(ctx, caso_id, estado="falha")
    _modo(ctx, "ok")
    assert _rodar(ctx)[1].chamadas == 0  # falha com a mesma entrada fica
    estados, rel = _rodar(ctx, refazer_falhas=True)
    assert rel.chamadas == 5 and estados["ok"] == 5 and estados["falha"] == 0
    for caso_id in OK:
        _confere(ctx, caso_id)


def test_11_cinco_rodadas_de_503_viram_falha(ctx):
    _sql(ctx, "delete from clima_atividade")
    _modo(ctx, "503")
    for rodada in range(1, 5):
        estados, _ = _rodar(ctx)
        assert estados["pendente"] == 5 and estados["falha"] == 0
        assert {t for (t,) in _sql(ctx, "select tentativas from clima_atividade")} == {rodada}
    estados, _ = _rodar(ctx)
    assert estados["falha"] == 5 and estados["pendente"] == 0
    erros = [e for (e,) in _sql(ctx, "select erro from clima_atividade")]
    assert all(e.startswith("5 rodadas sem sucesso: HTTP 503") for e in erros)
    _modo(ctx, "ok")
    assert _rodar(ctx, refazer_falhas=True)[0]["ok"] == 5  # deixa o clima ok para os testes de privacidade


# ---------------------------------------------------------------- 4. privacidade
def test_12_so_posicao_arredondada_e_horario_vao_para_fora(ctx):
    """Nenhuma chamada leva atleta, nome, arquivo ou coordenada exata; so latitude/longitude (2 casas) e datas."""
    _sql(ctx, "delete from clima_atividade")
    _modo(ctx, "ok")
    _rodar(ctx)
    pedidos = ctx["estado"]["pedidos"]
    assert len(pedidos) == 5
    permitidos = {"latitude", "longitude", "start_date", "end_date", "hourly", "wind_speed_unit", "timezone"}
    for p in pedidos:
        q = dict(p.url.params)
        assert set(q) == permitidos
        assert q["latitude"] == "12.35" and q["longitude"] == "-45.68"
        assert p.url.host == "archive-api.open-meteo.com"
        cabecalhos = {k: v for k, v in p.headers.items() if k != "user-agent"}  # o user-agent so nomeia o app
        assert p.headers["user-agent"].startswith("treino-contexto/")
        bruto = str(p.url) + str(cabecalhos) + p.content.decode()
        for proibido in ("Atleta", "Ficticio", "treino", "3000000", "12.3456", "45.6789", ".fit"):
            assert proibido not in bruto, proibido


def test_13_nada_do_trajeto_no_banco(ctx):
    colunas = {r[1] for r in _sql(ctx, "pragma table_info(atividade)")}
    assert {c for c in colunas if "lat" in c or "lon" in c or "pos" in c} == {"inicio_lat", "inicio_lon"}
    clima_cols = {r[1] for r in _sql(ctx, "pragma table_info(clima_atividade)")}
    assert not {c for c in clima_cols if "lat" in c or "lon" in c or "pos" in c or "trajeto" in c}
    tabelas = {r[0] for r in _sql(ctx, "select name from sqlite_master where type='table'")}
    assert not {t for t in tabelas if "ponto" in t or "trajeto" in t or "track" in t or "record" in t.replace("recorde_pessoal", "")}
    for lat, lon in _sql(ctx, "select inicio_lat, inicio_lon from atividade where inicio_lat is not null"):
        assert round(lat, 2) == lat and round(lon, 2) == lon  # 2 casas, nunca a posicao exata


def test_14_posicao_fora_da_resposta_e_do_openapi(ctx):
    for caso_id in OK + CALCULADOS:
        atleta, id_ = _atividade(ctx, caso_id)
        r = ctx["client"].get(f"/atletas/{atleta}/atividades/{id_}")
        assert "inicio_lat" not in r.text and "inicio_lon" not in r.text
        assert "12.35" not in r.text and "45.68" not in r.text
    esquema = ctx["client"].get("/openapi.json").text
    assert "inicio_lat" not in esquema and "inicio_lon" not in esquema
    assert json.loads(esquema)["components"]["schemas"]["AtividadeOut"]["properties"]["clima"]


def test_15_404_do_get(ctx):
    r = ctx["client"].get("/atletas/9999/atividades/1")
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}
    r = ctx["client"].get(f"/atletas/{ctx['atleta_fit']}/atividades/{_atividade(ctx, 'json_corrida_ar_livre')[1]}")
    assert r.status_code == 404 and r.json() == {"detail": "atividade não encontrada"}
