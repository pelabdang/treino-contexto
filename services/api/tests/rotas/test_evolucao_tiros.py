"""Endpoint JSON da evolução dos tiros de 1 km (issue #16), sobre um banco com as fixtures importadas."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import app

ZIP = Path(__file__).parents[4] / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"


@pytest.fixture
def importar_fixtures(session):
    from worker.importar_garmin import importar
    importar(session, ZIP, "Atleta Ficticio")
    return session.query(Atleta).one()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _url(atleta, q=""):
    return f"/atletas/{atleta.id}/evolucao/tiros-1km{q}"


def test_json_com_os_valores_do_oraculo(client, importar_fixtures):
    r = client.get(_url(importar_fixtures))
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"atleta_id", "metrica", "versao_calculo", "unidades", "periodo", "sessoes"}
    assert j["atleta_id"] == importar_fixtures.id and j["metrica"] == "tiros_1km"
    assert j["versao_calculo"] == "tiros_1km@1"
    assert j["unidades"] == {"pace": "s/km", "fc": "bpm", "distancia": "m", "duracao": "s"}
    assert j["periodo"] is None
    a, b = j["sessoes"]
    assert set(a) == {"atividade_id", "data", "inicio", "n_tiros", "pace_medio_s_km", "pace_medio",
                      "fc_media", "tiros"}
    assert (a["data"], a["inicio"], a["n_tiros"]) == ("2025-03-04", "2025-03-04T09:00:00Z", 6)
    assert (a["pace_medio_s_km"], a["pace_medio"], a["fc_media"]) == (250.8, "4:11", 170.3)
    assert (b["data"], b["n_tiros"]) == ("2025-03-11", 5)
    assert (b["pace_medio_s_km"], b["pace_medio"], b["fc_media"]) == (237.0, "3:57", 171.8)
    assert len(a["tiros"]) == 6 and len(b["tiros"]) == 5
    assert a["tiros"][0] == {"ordem": 1, "distancia_m": 1000.0, "duracao_s": 255.0, "pace_s_km": 255.0,
                             "fc_media": 165.0}
    assert [t["ordem"] for t in a["tiros"]] == [1, 3, 5, 7, 9, 11]


def test_periodo_com_um_filtro_so(client, importar_fixtures):
    j = client.get(_url(importar_fixtures, "?inicio=2025-03-05")).json()
    assert j["periodo"] == {"inicio": "2025-03-05", "fim": None}
    assert [s["data"] for s in j["sessoes"]] == ["2025-03-11"]
    j = client.get(_url(importar_fixtures, "?fim=2025-03-04")).json()
    assert j["periodo"] == {"inicio": None, "fim": "2025-03-04"}
    assert [s["data"] for s in j["sessoes"]] == ["2025-03-04"]
    j = client.get(_url(importar_fixtures, "?inicio=2025-03-04&fim=2025-03-11")).json()
    assert len(j["sessoes"]) == 2 and j["periodo"] == {"inicio": "2025-03-04", "fim": "2025-03-11"}


def test_atleta_inexistente_404(client, importar_fixtures):
    r = client.get("/atletas/9999/evolucao/tiros-1km")
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}


def test_atleta_sem_sessoes_200_lista_vazia(client, session):
    atleta = Atleta(nome="Sem treinos")
    session.add(atleta)
    session.commit()
    r = client.get(_url(atleta))
    assert r.status_code == 200
    assert r.json()["sessoes"] == [] and r.json()["versao_calculo"] == "tiros_1km@1"


@pytest.mark.parametrize("q", ["?inicio=ontem", "?fim=2025-13-40", "?inicio=2025-3"])
def test_data_invalida_422(client, importar_fixtures, q):
    assert client.get(_url(importar_fixtures, q)).status_code == 422


def test_atleta_id_nao_numerico_422(client):
    assert client.get("/atletas/abc/evolucao/tiros-1km").status_code == 422


def test_esquema_no_openapi(client):
    j = client.get("/openapi.json").json()
    assert "/atletas/{atleta_id}/evolucao/tiros-1km" in j["paths"]
    esquemas = j["components"]["schemas"]
    assert {"EvolucaoTiros1km", "SessaoOut", "TiroOut", "Periodo", "Unidades"} <= set(esquemas)
    assert "pace_medio" in esquemas["SessaoOut"]["properties"]


def test_inicio_utc_de_treino_noturno(client, importar_fixtures, session):
    """22:30 local (UTC-3) = 01:30 UTC do dia seguinte: `data` e a local, `inicio` e o UTC."""
    from datetime import datetime, timezone
    a = session.query(Atividade).filter_by(fonte_id="1000000001").one()
    a.inicio = datetime(2025, 3, 5, 1, 30, tzinfo=timezone.utc)
    session.commit()
    s = client.get(_url(importar_fixtures)).json()["sessoes"][0]
    assert (s["data"], s["inicio"]) == ("2025-03-04", "2025-03-05T01:30:00Z")


PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"


def _png(client, atleta, q=""):
    return client.get(f"/atletas/{atleta.id}/evolucao/tiros-1km.png{q}")


def test_png(client, importar_fixtures):
    r = _png(client, importar_fixtures)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content.startswith(PNG_ASSINATURA)
    import struct
    assert struct.unpack(">II", r.content[16:24]) == (1600, 1000)


def test_png_e_o_mesmo_do_render_png(client, importar_fixtures, session):
    from app.graficos.tiros_1km import render_png
    from app.servicos.evolucao_tiros import serie_tiros_1km
    esperado = render_png(serie_tiros_1km(session, importar_fixtures.id), importar_fixtures.nome)
    assert _png(client, importar_fixtures).content == esperado


def test_png_com_filtro_e_vazio(client, importar_fixtures):
    r = _png(client, importar_fixtures, "?inicio=2030-01-01")  # sem sessoes: gera o PNG com o aviso
    assert r.status_code == 200 and r.content.startswith(PNG_ASSINATURA)
    assert r.content != _png(client, importar_fixtures).content


def test_png_404_e_422(client, importar_fixtures):
    assert client.get("/atletas/9999/evolucao/tiros-1km.png").status_code == 404
    assert _png(client, importar_fixtures, "?fim=xx").status_code == 422


def test_png_no_openapi(client):
    j = client.get("/openapi.json").json()
    assert "image/png" in j["paths"]["/atletas/{atleta_id}/evolucao/tiros-1km.png"]["get"]["responses"]["200"]["content"]
