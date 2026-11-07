"""QA de ponta a ponta da Meta 5, a deteccao de esforcos (issue #172, ADR 0008 e 0009).

Segue o guia `docs/produto/meta-5-como-rodar.md`: migracoes (alembic, ate a 0007) -> importacao das fixtures da Meta 1,
dos sete FIT de esforcos e da exportacao multiesporte (CLI `worker.importar_garmin`, sem `--com-clima`, portanto sem
rede) -> `worker.detectar_esforcos` -> API (TestClient) conferida contra o oraculo de `esforcos-oraculo.md` ->
`worker.reclassificar` (`tiros_1km@6`), JSON, PNG e CSV -> treino de transicao (`worker.sugerir_transicao` e as rotas,
com PUT, DELETE, 400 e 404) -> `worker.reclassificar_multiesporte`. Num SQLite temporario; so dado sintetico.

Os testes seguem a ordem do arquivo e dividem o mesmo banco (como os e2e das Metas 2 a 4), entao a ordem importa.
"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures"
ZIP = FIXTURES / "garmin" / "exportacao_minima.zip"
PASTA_FIT = FIXTURES / "garmin" / "esforcos"
MULTI = FIXTURES / "multiesporte" / "exportacao_multiesporte.json"
ORACULO = RAIZ / "services" / "api" / "tests" / "metricas" / "test_esforcos_oraculo.py"


def _oraculo():
    """Carrega `ESPERADO` do oraculo da #161 (blocos calculados a mao), sem duplicar a tabela."""
    api_app = str(RAIZ / "services" / "api")
    if api_app not in sys.path:
        sys.path.insert(0, api_app)
    spec = importlib.util.spec_from_file_location("oraculo_esforcos_e2e", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ESPERADO


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local (a mesma guarda das Metas 3 e 4)."""
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


def _roda(args, env, cwd=RAIZ):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r.stdout


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.session import get_session
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    base = tmp_path_factory.mktemp("e2e_meta5")
    url = f"sqlite:///{base / 'treino.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    env.pop("VIRTUAL_ENV", None)
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem (5432, 5433...)
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    eng = create_engine(url)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: base / "fit"
    try:
        yield {"client": TestClient(app), "eng": eng, "env": env}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _worker(ctx, modulo, *args):
    return _roda(["-m", f"worker.{modulo}", *args], ctx["env"])


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _get(ctx, caminho, status=200):
    r = ctx["client"].get(caminho)
    assert r.status_code == status, (caminho, r.status_code, r.text[:300])
    return r


def _atividade(ctx, atleta, atividade):
    return _get(ctx, f"/atletas/{atleta}/atividades/{atividade}").json()


def _ids_fit(ctx):
    """Ids das sete atividades dos FIT de esforcos, na ordem do oraculo (E1 a E7 = `fit-1-...` a `fit-7-...`)."""
    linhas = _sql(ctx, "select id, fonte_id from atividade where fonte_id like 'fit-%' order by inicio")
    assert len(linhas) == 7
    return [i for i, _ in linhas]


# ---------------------------------------------------------------- 1. migracoes e importacao
def test_1_migracoes_ate_a_0009(ctx):
    # a 0008 e a 0009 (Meta 6, #140 e #174) so acrescentam tabelas de saude; o fluxo da Meta 5 nao as usa
    assert _sql(ctx, "select version_num from alembic_version") == [("0009",)]
    tabelas = {t for (t,) in _sql(ctx, "select name from sqlite_master where type='table'")}
    assert {"bloco_atividade", "rotulo_transicao", "limiar_atleta", "zona_fc_atleta"} <= tabelas


def test_2_importacao_sem_rede_e_idempotente(ctx):
    s1 = _worker(ctx, "importar_garmin", str(ZIP), "--atleta", "Atleta Ficticio")
    s2 = _worker(ctx, "importar_garmin", str(PASTA_FIT), "--atleta", "Atleta Ficticio")
    assert "inseridas=5 atualizadas=0 ignoradas=0 avisos=1" in s1
    assert "inseridas=7 atualizadas=0 ignoradas=0 avisos=0" in s2
    assert "clima: nao buscado (sem rede)" in s1 and "clima: nao buscado (sem rede)" in s2
    assert _sql(ctx, "select count(*) from atividade") == [(12,)]
    assert _sql(ctx, "select count(*) from clima_atividade") == [(0,)]  # nada buscado
    s3 = _worker(ctx, "importar_garmin", str(PASTA_FIT), "--atleta", "Atleta Ficticio")
    assert "inseridas=0" in s3
    assert _sql(ctx, "select count(*) from atividade") == [(12,)]  # reimportar nao duplica


# ---------------------------------------------------------------- 2. esforcos: comando, banco e API
def test_3_detectar_esforcos_conta_e_idempotencia(ctx):
    _sql(ctx, "delete from bloco_atividade")
    s1 = _worker(ctx, "detectar_esforcos", "--atleta-id", "1")
    assert "esforcos esforcos@1 do atleta 1" in s1
    assert "atividades processadas: 11 (gravadas de novo: 10, sem mudança: 1, sem blocos: 1)" in s1
    assert "corrida: esforcos=38 treinos-chave=1" in s1
    assert "ciclismo: esforcos=5 treinos-chave=0" in s1
    assert "esforcos por faixa: ciclismo t4=5, corrida d1000=16, corrida d1500=3, corrida d400=18" in s1
    assert "referencia da propria atividade (sem historico): 2 atividades" in s1
    antes = _sql(ctx, "select id, atividade_id, ordem, versao_deteccao from bloco_atividade order by id")
    s2 = _worker(ctx, "detectar_esforcos", "--atleta-id", "1")
    assert "gravadas de novo: 0, sem mudança: 11" in s2
    assert _sql(ctx, "select id, atividade_id, ordem, versao_deteccao from bloco_atividade order by id") == antes
    assert {v for *_, v in antes} == {"esforcos@1"}  # nenhuma linha duplicada: (atividade, ordem) e unica


def test_4_blocos_na_api_batem_com_o_oraculo(ctx):
    """Cada bloco dos sete FIT: categoria, faixa, treino-chave, distancia, duracao, FC, pace/velocidade e parada."""
    esperado = _oraculo()
    for (nome, (modalidade, _ref, blocos)), ativ in zip(esperado.items(), _ids_fit(ctx)):
        if nome == "esforcos_ciclismo_lap_automatico.fit":
            continue  # o oraculo usa ref. de 20 km/h; no banco compartilhado a referencia e o historico (teste 4b)
        j = _atividade(ctx, 1, ativ)
        assert j["modalidade"] == modalidade, nome
        e = j["esforcos"]
        assert e["versao"] == "esforcos@1"
        assert len(e["blocos"]) == len(blocos), nome
        for api, b in zip(e["blocos"], blocos):
            quem = (nome, api["ordem"])
            assert api["categoria"] == b.categoria, quem
            assert api["faixa"] == b.faixa, quem
            assert api["treino_chave"] == b.treino_chave, quem
            assert api["distancia_m"] == pytest.approx(b.distancia_m, abs=0.5), quem
            assert api["duracao_s"] == pytest.approx(b.duracao_s, abs=0.5), quem
            assert api["fc_media"] == pytest.approx(b.fc_media, abs=0.1), quem
            chave = "pace_s_km" if modalidade == "corrida" else "velocidade_kmh"
            assert api[chave] == pytest.approx(b.intensidade, abs=0.1), quem
            assert (api["parada_apos_s"] or 0) == pytest.approx(b.parada_apos_s, abs=0.5), quem


def test_4b_pedal_com_lap_cortado_sozinho_bate_com_o_oraculo(ctx, tmp_path):
    """O FIT 7 (ref. 20 km/h no oraculo) importado sozinho: sem historico, a referencia e a da propria atividade.

    No banco compartilhado ele vem depois do pedal de 4 min (FIT 6, ~26 km/h) e a referencia de ciclismo passa a ser esse
    historico: o bloco de 20 min a 24 km/h deixa de ser esforco (ver o relatorio da #172). Aqui o oraculo vale."""
    pasta = tmp_path / "solo"
    pasta.mkdir()
    (pasta / "pedal.fit").write_bytes((PASTA_FIT / "esforcos_ciclismo_lap_automatico.fit").read_bytes())
    url = f"sqlite:///{tmp_path / 'solo.db'}"
    env = {**ctx["env"], "DATABASE_URL": url}
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    _roda(["-m", "worker.importar_garmin", str(pasta), "--atleta", "Atleta Solo"], env)
    saida = _roda(["-m", "worker.detectar_esforcos", "--atleta-id", "1"], env)
    assert "ciclismo: esforcos=1" in saida
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            linhas = c.execute(text("select categoria, faixa, distancia_m, duracao_s from bloco_atividade order by ordem")).all()
    finally:
        eng.dispose()
    oraculo = _oraculo()["esforcos_ciclismo_lap_automatico.fit"][2]
    assert [(l[0], l[1]) for l in linhas] == [(b.categoria, b.faixa) for b in oraculo]
    assert [round(l[2]) for l in linhas] == [round(b.distancia_m) for b in oraculo]
    assert [round(l[3]) for l in linhas] == [round(b.duracao_s) for b in oraculo]


def test_5_lap_cortado_vira_um_esforco_e_aquecimento_nunca_e_esforco(ctx):
    ids = _ids_fit(ctx)
    # 3 x 1500 m cortados em 1000 + 500 m (FIT 2): tres esforcos d1500, nunca seis voltas soltas
    blocos = _atividade(ctx, 1, ids[1])["esforcos"]["blocos"]
    esforcos = [b for b in blocos if b["categoria"] == "esforco"]
    assert [b["faixa"] for b in esforcos] == ["d1500"] * 3
    assert all(b["distancia_m"] == pytest.approx(1500, abs=0.5) for b in esforcos)
    # ciclismo: o bloco de 20 min cortado em 5 km + 3 km (FIT 7) esta no teste 4b; aqui, com o historico, nao e esforco
    pedal = _atividade(ctx, 1, ids[6])["esforcos"]["blocos"]
    assert len(pedal) == 3 and all(b["categoria"] != "esforco" for b in pedal)
    # em nenhuma atividade o primeiro ou o ultimo bloco rotulado aquecimento/desaquecimento conta como esforco
    for ativ in ids:
        for b in _atividade(ctx, 1, ativ)["esforcos"]["blocos"]:
            if b["categoria"] in ("aquecimento", "desaquecimento"):
                assert b["faixa"] is None and not b["treino_chave"]
    # continuo forte (FIT 3): um bloco, esforco sem faixa e treino-chave; rodagem leve (FIT 4): leve, sem esforco
    continuo = _atividade(ctx, 1, ids[2])["esforcos"]
    assert continuo["treino_chave"] is True
    assert [(b["categoria"], b["faixa"]) for b in continuo["blocos"]] == [("esforco", None)]
    leve = _atividade(ctx, 1, ids[3])["esforcos"]
    assert [b["categoria"] for b in leve["blocos"]] == ["leve"] and leve["treino_chave"] is False


def test_6_textos_prontos_e_referencia_da_atividade(ctx):
    ids = _ids_fit(ctx)
    j8 = _atividade(ctx, 1, ids[2])
    assert (j8["duracao"], j8["distancia"], j8["pace_medio"]) == ("0:36:00", "8,00 km", "4:30")
    assert j8["esforcos"]["referencia_da_atividade"] is False
    j11 = _atividade(ctx, 1, ids[5])
    assert j11["pace_medio"] is None and j11["esforcos"]["referencia_da_atividade"] is True
    t4 = j11["esforcos"]["blocos"][1]
    assert (t4["faixa"], t4["faixa_rotulo"], t4["duracao"], t4["distancia"], t4["velocidade"]) == (
        "t4", "4 min", "4:00", "2,40 km", "36,0 km/h")


def test_7_natacao_sem_esforcos_404_e_versao_nova_redetecta(ctx):
    nat = _sql(ctx, "select id from atividade where modalidade='natacao'")[0][0]
    assert _atividade(ctx, 1, nat)["esforcos"] is None
    _get(ctx, "/atletas/1/atividades/9999", 404)
    _get(ctx, "/atletas/99/atividades/1", 404)
    # versao diferente gravada: a API avisa, o comando redetecta so as atividades afetadas e volta a esforcos@1
    _sql(ctx, "update bloco_atividade set versao_deteccao='esforcos@0'")
    assert _get(ctx, "/atletas/1/evolucao/tiros-1km").json()["reclassificacao_pendente"] is True
    s = _worker(ctx, "detectar_esforcos", "--atleta-id", "1")
    assert "gravadas de novo: 10, sem mudança: 1" in s
    assert _sql(ctx, "select distinct versao_deteccao from bloco_atividade") == [("esforcos@1",)]
    assert _sql(ctx, "select count(*) from bloco_atividade") == [(82,)]  # sem duplicar


# ---------------------------------------------------------------- 3. serie de tiros pelos esforcos (@5)
def test_8_reclassificar_tiros_1km_arroba_5(ctx):
    _sql(ctx, "update segmento set versao_deteccao='tiros_1km@4'")
    antes = _get(ctx, "/atletas/1/evolucao/tiros-1km").json()
    assert antes["versao_calculo"] == "tiros_1km@6" and antes["reclassificacao_pendente"] is True
    assert "reclassificadas 9 corridas do atleta 1" in _worker(ctx, "reclassificar", "--atleta-id", "1")
    j = _get(ctx, "/atletas/1/evolucao/tiros-1km").json()
    assert j["reclassificacao_pendente"] is False
    assert [(s["data"], s["n_tiros"]) for s in j["sessoes"]] == [
        ("2025-03-04", 6), ("2025-03-11", 5), ("2025-05-12", 5)]
    # melhor pace e FC do melhor tiro como valores principais; a ultima sessao vem dos FIT (5 x 1 km do treino misto)
    assert [s["pace_melhor"] for s in j["sessoes"]] == ["4:08", "3:54", "4:10"]
    assert [s["fc_melhor_tiro"] for s in j["sessoes"]] == [175.0, 177.0, 160.0]
    for s in j["sessoes"]:
        assert s["pace_melhor_s_km"] <= s["pace_medio_s_km"]
        assert len(s["tiros"]) == s["n_tiros"]
    # rodar de novo nao muda nada
    assert "reclassificadas" in _worker(ctx, "reclassificar", "--atleta-id", "1")
    assert _get(ctx, "/atletas/1/evolucao/tiros-1km").json() == j


def test_9_png_e_csv_trazem_o_melhor_tiro(ctx):
    from app.graficos.tiros_1km import COLUNAS_CSV, linhas_csv
    from app.servicos.evolucao_tiros import serie_tiros_1km

    r = _get(ctx, "/atletas/1/evolucao/tiros-1km.png")
    assert r.headers["content-type"] == "image/png" and r.content[:8] == b"\x89PNG\r\n\x1a\n"
    largura, altura = int.from_bytes(r.content[16:20], "big"), int.from_bytes(r.content[20:24], "big")
    assert (largura, altura) == (1600, 1000)
    with Session(ctx["eng"]) as s:
        linhas = linhas_csv(serie_tiros_1km(s, 1))
    assert "pace_melhor_min_km" in COLUNAS_CSV and "fc_melhor_tiro" in COLUNAS_CSV
    assert [(l["pace_melhor_min_km"], l["fc_melhor_tiro"]) for l in linhas] == [
        ("4:08", "175.0"), ("3:54", "177.0"), ("4:10", "160.0")]


# ---------------------------------------------------------------- 4. treino de transicao
def _brick(ctx):
    """Quatro atividades inventadas: dois treinos ciclismo e depois corrida, com 2 e 3 minutos entre as partes."""
    _sql(ctx, """insert into atividade (atleta_id,fonte,fonte_id,modalidade,inicio,duracao_s,distancia_m,fc_media)
        values (1,'guia','brick-1a','ciclismo','2025-06-02 10:00:00',3600,30000,140),
               (1,'guia','brick-1b','corrida','2025-06-02 11:02:00',1800,6000,155),
               (1,'guia','brick-2a','ciclismo','2025-06-09 10:00:00',3600,31000,142),
               (1,'guia','brick-2b','corrida','2025-06-09 11:03:00',1800,6200,158)""")
    return [i for (i,) in _sql(ctx, "select id from atividade where fonte='guia' order by id")]


def test_10_sugerir_transicao_e_idempotente(ctx):
    ids = _brick(ctx)
    assert ids == [13, 14, 15, 16]
    s1 = _worker(ctx, "sugerir_transicao", "--atleta-id", "1")
    assert "atividades: 16 (elegiveis: 16)" in s1 and "sugeridas pela regra: 4" in s1
    assert "inseridas: 4, atualizadas (versao nova): 0, removidas: 0, sem mudanca: 0" in s1
    s2 = _worker(ctx, "sugerir_transicao", "--atleta-id", "1")
    assert "inseridas: 0, atualizadas (versao nova): 0, removidas: 0, sem mudanca: 4" in s2


def test_11_listar_e_comparar(ctx):
    grupos = _get(ctx, "/atletas/1/treinos-de-transicao").json()["grupos"]
    assert [(g["grupo_id"], g["forma"], g["incompleto"]) for g in grupos] == [
        (15, "ciclismo>corrida", False), (13, "ciclismo>corrida", False)]
    g15, g13 = grupos
    assert [t["intervalo_estimado"] for t in (g15["transicoes"][0], g13["transicoes"][0])] == ["3:00", "2:00"]
    assert (g15["tempo_total"], g13["tempo_total"]) == ("1:33:00", "1:32:00")
    assert [p["ritmo"] for p in g15["partes"]] == ["31,0 km/h", "4:50 /km"]
    assert [p["ritmo"] for p in g13["partes"]] == ["30,0 km/h", "5:00 /km"]
    c = _get(ctx, "/atletas/1/treinos-de-transicao/comparar?a=13&b=15").json()
    assert c["total"]["soma_duracoes_dif"] == "0:00"
    assert c["total"]["soma_intervalos_estimados_dif"] == "+1:00"
    assert c["total"]["tempo_total_dif"] == "+1:00"
    assert c["total"]["fc_dif_texto"] == "+2 bpm"
    assert c["partes"][0]["ritmo_dif_texto"] == "+1,0 km/h" and c["partes"][1]["ritmo_dif_texto"] == "-0:10 /km"


def test_12_corrigir_desfazer_e_erros(ctx):
    cli = ctx["client"]
    base = "/atletas/1/atividades"
    r = cli.put(f"{base}/14/transicao", json={"transicao": False})
    assert (r.status_code, r.json()) == (200, {"valor": False, "origem": "atleta"})
    # a regra rodando de novo nao desfaz a correcao do atleta; o treino deixa de ser par: a parte que sobra
    # (o pedal 13) fica como grupo incompleto (comportamento coberto por test_nao_so_numa_parte_deixa_a_outra_incompleta)
    s = _worker(ctx, "sugerir_transicao", "--atleta-id", "1")
    assert "correcoes do atleta (nao tocadas): 1 (em 1 delas a regra sugere sim)" in s
    grupos = _get(ctx, "/atletas/1/treinos-de-transicao").json()["grupos"]
    assert [(g["grupo_id"], g["forma"], g["incompleto"]) for g in grupos] == [
        (15, "ciclismo>corrida", False), (13, "ciclismo", True)]
    r = cli.delete(f"{base}/14/transicao")
    assert (r.status_code, r.json()) == (200, {"valor": True, "origem": "sugerido"})
    assert [g["grupo_id"] for g in _get(ctx, "/atletas/1/treinos-de-transicao").json()["grupos"]] == [15, 13]
    # "sim" numa atividade que a regra nao sugeriu: vira grupo incompleto de uma modalidade
    r = cli.put(f"{base}/9/transicao", json={"transicao": True})
    assert (r.status_code, r.json()) == (200, {"valor": True, "origem": "atleta"})
    grupos = _get(ctx, "/atletas/1/treinos-de-transicao").json()["grupos"]
    assert ("corrida", True) in [(g["forma"], g["incompleto"]) for g in grupos]
    r = cli.get("/atletas/1/treinos-de-transicao/comparar?a=13&b=9")
    assert r.status_code == 400 and "mesma sequência de modalidades" in r.json()["detail"]
    r = cli.get("/atletas/1/treinos-de-transicao/comparar?a=13&b=8")
    assert r.status_code == 404 and r.json()["detail"] == "treino de transição não encontrado"
    # desfazer o "sim" da 9 (sem rotulo gravado de regra: volta a "nao", sem origem)
    r = cli.delete(f"{base}/9/transicao")
    assert (r.status_code, r.json()) == (200, {"valor": False, "origem": None})
    # corpo invalido, atividade e atleta que nao existem
    assert cli.put(f"{base}/9/transicao", json={"transicao": "x"}).status_code == 422
    assert cli.put(f"{base}/9999/transicao", json={"transicao": True}).status_code == 404
    assert cli.delete(f"{base}/9999/transicao").status_code == 404
    assert cli.get("/atletas/1/treinos-de-transicao/comparar?a=13").status_code == 422
    assert cli.get("/atletas/99/treinos-de-transicao").status_code == 404


# ---------------------------------------------------------------- 5. multiesporte
def test_13_reclassificar_multiesporte(ctx):
    s = _worker(ctx, "importar_garmin", str(MULTI), "--atleta", "Atleta Multiesporte")
    assert "inseridas=7" in s
    linhas = _sql(ctx, "select id, modalidade, subtipo from atividade where atleta_id=2 order by id")
    assert [(m, st) for _, m, st in linhas] == [
        ("outra", "multiesporte_pai"), ("natacao", "aguas_abertas"), ("outra", "troca"),
        ("ciclismo", None), ("outra", "troca"), ("corrida", None), ("corrida", None)]
    marcados = [i for i, _, st in linhas if st in ("multiesporte_pai", "troca")]
    assert len(marcados) == 3
    # banco importado antes do subtipo: dry-run nao grava, a rodada grava, a seguinte nao muda nada
    _sql(ctx, "update atividade set subtipo = null where id in (:a, :b, :c)", a=marcados[0], b=marcados[1], c=marcados[2])
    args = ["--exportacao", str(MULTI), "--atleta-id", "2"]
    seco = _worker(ctx, "reclassificar_multiesporte", *args, "--dry-run")
    assert "NULL -> multiesporte_pai: 1" in seco and "NULL -> troca: 2" in seco
    assert "atividades que mudariam (dry-run, nada gravado): 3" in seco
    assert _sql(ctx, "select count(*) from atividade where subtipo in ('troca','multiesporte_pai')") == [(0,)]
    assert "atividades que mudaram: 3" in _worker(ctx, "reclassificar_multiesporte", *args)
    assert "atividades que mudaram: 0" in _worker(ctx, "reclassificar_multiesporte", *args)
    # pai e troca ficam fora da regra de transicao; as partes viram um grupo natacao>ciclismo>corrida
    s = _worker(ctx, "sugerir_transicao", "--atleta-id", "2")
    assert "elegiveis: 4" in s and "sugeridas pela regra: 3" in s
    grupos = _get(ctx, "/atletas/2/treinos-de-transicao").json()["grupos"]
    assert [(g["forma"], g["incompleto"]) for g in grupos] == [("natacao>ciclismo>corrida", False)]
    # os blocos e a serie de tiros do atleta 1 nao mudaram com tudo isso
    assert _sql(ctx, "select count(*) from bloco_atividade where atividade_id > 12") == [(0,)]
    assert len(_get(ctx, "/atletas/1/evolucao/tiros-1km").json()["sessoes"]) == 3
