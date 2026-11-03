"""Endpoint JSON da evolução dos tiros de 1 km (issue #16), sobre um banco com as fixtures importadas."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import app
from app.metricas.tiros_1km import VERSAO

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
    assert set(j) == {"atleta_id", "metrica", "versao_calculo", "reclassificacao_pendente", "unidades", "periodo", "sessoes"}
    assert j["atleta_id"] == importar_fixtures.id and j["metrica"] == "tiros_1km"
    assert j["versao_calculo"] == VERSAO and j["reclassificacao_pendente"] is False
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
                             "pace": "4:15", "fc_media": 165.0}
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
    assert r.json()["sessoes"] == [] and r.json()["versao_calculo"] == VERSAO


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


def test_esteira_sintetica_fora_do_json_e_do_png(client, importar_fixtures, session):
    from datetime import datetime, timezone

    from app.db.models import Segmento
    from app.servicos.evolucao_tiros import classificar_atividades
    ativ = Atividade(atleta_id=importar_fixtures.id, fonte="garmin_export", fonte_id="esteira-sintetica",
                     modalidade="corrida", subtipo="esteira", fuso_min=-180,
                     inicio=datetime(2025, 3, 8, 12, 0, tzinfo=timezone.utc), duracao_s=2000, distancia_m=7000)
    voltas = [("warmup", 1000, 360)] + [("active", 1000, 230), ("rest", 200, 90)] * 5
    for i, (intens, d, du) in enumerate(voltas):
        ativ.segmentos.append(Segmento(ordem=i, tipo="volta", duracao_s=du, distancia_m=d, intensidade=intens))
    session.add(ativ)
    session.commit()
    classificar_atividades(session, importar_fixtures.id)
    j = client.get(_url(importar_fixtures)).json()
    assert [s["data"] for s in j["sessoes"]] == ["2025-03-04", "2025-03-11"]
    assert ativ.id not in [s["atividade_id"] for s in j["sessoes"]]
    assert _png(client, importar_fixtures).status_code == 200


def test_tiro_com_tudo_em_uma_casa_e_pace_do_valor_cru(client, importar_fixtures, session):
    """239,46 s/km: texto `3:59` (do valor cru), número 239,5 (1 casa). Formatar o número daria 4:00."""
    from app.db.models import Segmento
    a = session.query(Atividade).filter_by(fonte_id="1000000001").one()
    seg = next(s for s in a.segmentos if s.ordem == 1)
    seg.distancia_m, seg.duracao_s, seg.fc_media = 1000.04, 239.46 * 1.00004, 165.46
    session.commit()
    t = client.get(_url(importar_fixtures)).json()["sessoes"][0]["tiros"][0]
    assert (t["pace_s_km"], t["pace"]) == (239.5, "3:59")
    assert (t["distancia_m"], t["fc_media"]) == (1000.0, 165.5)
    assert t["duracao_s"] == round(239.46 * 1.00004, 1)


def test_segmento_sem_distancia_vira_null_nunca_zero(client, importar_fixtures, session):
    a = session.query(Atividade).filter_by(fonte_id="1000000001").one()
    seg = next(s for s in a.segmentos if s.ordem == 1)
    seg.distancia_m = None
    session.commit()
    t = client.get(_url(importar_fixtures)).json()["sessoes"][0]["tiros"]
    assert t[0]["distancia_m"] is None and t[0]["pace_s_km"] is None and t[0]["pace"] is None
    assert t[1]["distancia_m"] == 1000.0


def test_reclassificacao_pendente_com_versao_velha_sem_escrever_e_comando_limpa(client, importar_fixtures, session):
    from app.db.models import Segmento
    from worker.reclassificar import reclassificar
    a = session.query(Atividade).filter_by(fonte_id="1000000002").one()
    a.segmentos[0].versao_deteccao = "tiros_1km@1"
    session.commit()
    antes = sorted((s.id, s.tipo, s.versao_deteccao) for s in session.query(Segmento))
    j = client.get(_url(importar_fixtures)).json()
    assert j["reclassificacao_pendente"] is True
    assert j["versao_calculo"] == VERSAO  # sempre a regra atual, nunca a gravada
    # o GET não escreveu nada: nenhum segmento mudou e continua pendente na segunda leitura
    session.expire_all()
    assert sorted((s.id, s.tipo, s.versao_deteccao) for s in session.query(Segmento)) == antes
    assert client.get(_url(importar_fixtures)).json()["reclassificacao_pendente"] is True
    # o período olha só as corridas do filtro: a velha é de 2025-03-11
    assert client.get(_url(importar_fixtures, "?fim=2025-03-05")).json()["reclassificacao_pendente"] is False
    # depois do comando de reclassificação, volta a false
    reclassificar(session, importar_fixtures.id)
    j = client.get(_url(importar_fixtures)).json()
    assert j["reclassificacao_pendente"] is False and j["versao_calculo"] == VERSAO


def test_sem_sessoes_nao_esta_pendente(client, session):
    atleta = Atleta(nome="Sem treinos")
    session.add(atleta)
    session.commit()
    assert client.get(_url(atleta)).json()["reclassificacao_pendente"] is False


def test_inicio_depois_de_fim_422(client, importar_fixtures):
    r = client.get(_url(importar_fixtures, "?inicio=2025-03-11&fim=2025-03-04"))
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
    assert client.get(_url(importar_fixtures, "?inicio=2025-03-04&fim=2025-03-04")).status_code == 200
    r = client.get(f"/atletas/{importar_fixtures.id}/evolucao/tiros-1km.png?inicio=2025-03-11&fim=2025-03-04")
    assert r.status_code == 422


def test_contrato_no_openapi(client):
    j = client.get("/openapi.json").json()
    get_json = j["paths"]["/atletas/{atleta_id}/evolucao/tiros-1km"]["get"]
    get_png = j["paths"]["/atletas/{atleta_id}/evolucao/tiros-1km.png"]["get"]
    assert get_json["operationId"] == "evolucaoTiros1km" and get_png["operationId"] == "evolucaoTiros1kmPng"
    for op in (get_json, get_png):
        assert op["responses"]["404"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/Erro"}
    esq = j["components"]["schemas"]
    assert esq["Erro"]["required"] == ["detail"]
    assert set(esq["Unidades"]["required"]) == {"pace", "fc", "distancia", "duracao"}
    assert esq["EvolucaoTiros1km"]["properties"]["metrica"]["const"] == "tiros_1km"
    assert "reclassificacao_pendente" in esq["EvolucaoTiros1km"]["required"]
    assert "pace" in esq["TiroOut"]["required"]
