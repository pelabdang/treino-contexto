"""Endpoint da carga e carga no GET da atividade (issue #142, ADR 0010 itens 5 a 7), contra o oraculo da #137.

Fixtures sinteticas de tests/fixtures/garmin/carga/. Cargas calculadas a mao no oraculo (docs/metricas/carga-oraculo.md).
"""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, CargaAtividade
from app.db.session import get_session
from app.ingestao.importacao import importar
from app.ingestao.saude import importar_saude
from app.main import criar_app
from app.servicos.carga import calcular_carga_do_atleta
from fastapi.testclient import TestClient
from sqlalchemy import select

RAIZ = Path(__file__).resolve().parents[4]
PASTA = RAIZ / "tests" / "fixtures" / "garmin" / "carga"
_spec = importlib.util.spec_from_file_location(
    "_carga_oraculo_api", RAIZ / "services" / "api" / "tests" / "metricas" / "test_carga_oraculo.py")
_o = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _o
_spec.loader.exec_module(_o)
ESPERADO, SERIE, TOTAIS, TOTAIS_SEM_SAUDE = _o.ESPERADO, _o.SERIE, _o.TOTAIS, _o.TOTAIS_SEM_SAUDE
MOTIVOS = {"sem_dados_saude", "sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga"}


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def _atleta(session, zip_="exportacao_carga.zip", calcular=True):
    importar(session, str(PASTA / zip_), "Ana")
    importar_saude(session, str(PASTA / zip_), "Ana")
    atleta_id = session.scalars(select(Atleta)).one().id
    if calcular:
        calcular_carga_do_atleta(session, atleta_id)
    return atleta_id


def test_serie_bate_com_o_oraculo(session, client):
    atleta_id = _atleta(session)
    r = client.get(f"/atletas/{atleta_id}/carga")
    assert r.status_code == 200
    j = r.json()
    assert j["versao"] == "serie_carga@1" and j["versao_carga"] == "carga@1"
    assert j["aviso"] is None and j["periodo"] is None
    assert len(j["dias"]) == 43 and j["dias"][0]["data"] == "2025-03-05" and j["dias"][-1]["data"] == "2025-04-16"
    por_dia = {d["data"]: d for d in j["dias"]}
    for dia, esp in SERIE.items():
        d = por_dia[dia.isoformat()]
        assert d["carga"] == pytest.approx(esp.carga, abs=1e-5)
        assert d["ctl"] == pytest.approx(esp.ctl, abs=1e-5)
        assert d["atl"] == pytest.approx(esp.atl, abs=1e-5)
        assert d["tsb"] == pytest.approx(esp.tsb, abs=1e-5)
        assert d["aprendendo"] is esp.aprendendo
        assert (d["atividades"], d["calculadas"], d["sem_carga"]) == (esp.atividades, esp.calculadas, esp.sem_carga)
    t = j["totais"]
    assert t["atividades_importadas"] == TOTAIS["atividades_importadas"] and t["pendentes"] == 0
    assert t["calculadas"] == TOTAIS["calculadas"] and t["sem_carga_total"] == TOTAIS["sem_carga_total"]
    assert t["ignoradas_multiesporte"] == TOTAIS["ignoradas_multiesporte"]
    assert t["por_motivo"] == TOTAIS["por_motivo"] and set(t["por_motivo"]) == MOTIVOS


def test_periodo_recorta_so_os_dias(session, client):
    atleta_id = _atleta(session)
    j = client.get(f"/atletas/{atleta_id}/carga", params={"inicio": "2025-03-08", "fim": "2025-03-09"}).json()
    assert [d["data"] for d in j["dias"]] == ["2025-03-08", "2025-03-09"]
    assert j["periodo"] == {"inicio": "2025-03-08", "fim": "2025-03-09"}
    assert j["dias"][0]["ctl"] == pytest.approx(SERIE[_o.date(2025, 3, 8)].ctl, abs=1e-5)  # recursao parte do inicio real
    assert j["totais"]["calculadas"] == TOTAIS["calculadas"]  # totais sao do atleta todo


def test_periodo_invertido_e_422(session, client):
    atleta_id = _atleta(session)
    assert client.get(f"/atletas/{atleta_id}/carga", params={"inicio": "2025-04-01", "fim": "2025-03-01"}).status_code == 422


def test_atleta_inexistente_404(client):
    r = client.get("/atletas/999/carga")
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}


def test_atleta_sem_saude_serie_vazia_com_aviso(session, client):
    atleta_id = _atleta(session, "exportacao_carga_sem_saude.zip")
    j = client.get(f"/atletas/{atleta_id}/carga").json()
    assert j["dias"] == [] and j["aviso"] == "sem_carga_calculada"
    assert j["totais"]["calculadas"] == 0 and j["totais"]["sem_carga_total"] == TOTAIS_SEM_SAUDE["sem_carga_total"]
    assert j["totais"]["por_motivo"] == TOTAIS_SEM_SAUDE["por_motivo"]


def test_nada_calculado_conta_pendentes(session, client):
    atleta_id = _atleta(session, calcular=False)
    j = client.get(f"/atletas/{atleta_id}/carga").json()
    assert j["dias"] == [] and j["aviso"] == "sem_carga_calculada"
    t = j["totais"]
    assert t["pendentes"] == TOTAIS["atividades_importadas"] - TOTAIS["ignoradas_multiesporte"]
    assert t["calculadas"] == t["sem_carga_total"] == 0 and t["ignoradas_multiesporte"] == TOTAIS["ignoradas_multiesporte"]


def test_atleta_sem_atividades(session, client):
    a = Atleta(nome="Vazio")
    session.add(a)
    session.commit()
    j = client.get(f"/atletas/{a.id}/carga").json()
    assert j["dias"] == [] and j["aviso"] == "sem_carga_calculada" and j["totais"]["atividades_importadas"] == 0


def test_atividade_traz_a_carga_do_oraculo(session, client):
    atleta_id = _atleta(session)
    por_fonte = {int(f): i for f, i in session.execute(select(Atividade.fonte_id, Atividade.id))}
    vistos = set()
    for fonte, e in ESPERADO.items():
        j = client.get(f"/atletas/{atleta_id}/atividades/{por_fonte[fonte]}").json()["carga"]
        assert j["estado"] == e.estado and j["versao"] == "carga@1"
        assert set(j) == {"estado", "carga", "metodo", "cobertura_pct", "motivo", "versao"}  # nada de limiar
        assert j["motivo"] == e.motivo and j["metodo"] == e.metodo
        if e.estado == "calculada":
            assert j["carga"] == pytest.approx(e.carga, abs=1e-5)
            assert j["cobertura_pct"] == pytest.approx(e.cobertura_pct)
        else:
            assert j["carga"] is None
        vistos.add(fonte)
    ignoradas = set(por_fonte) - vistos
    assert len(ignoradas) == TOTAIS["ignoradas_multiesporte"]
    for fonte in ignoradas:
        assert client.get(f"/atletas/{atleta_id}/atividades/{por_fonte[fonte]}").json()["carga"] is None


def test_atividade_elegivel_sem_linha_e_pendente(session, client):
    a = Atleta(nome="Ana")
    session.add(a)
    session.commit()
    at = Atividade(atleta_id=a.id, fonte="teste", fonte_id="1", modalidade="corrida", duracao_s=1800.0,
                   inicio=datetime(2025, 3, 5, 9, tzinfo=timezone.utc))
    session.add(at)
    session.commit()
    assert client.get(f"/atletas/{a.id}/atividades/{at.id}").json()["carga"] == {
        "estado": "pendente", "carga": None, "metodo": None, "cobertura_pct": None, "motivo": None, "versao": None}


def test_versao_antiga_e_pendente_na_atividade_e_na_serie(session, client):
    atleta_id = _atleta(session)
    antes = client.get(f"/atletas/{atleta_id}/carga").json()
    linha = session.scalars(select(CargaAtividade).where(CargaAtividade.estado == "calculada")).first()
    linha.versao = "carga@0"
    session.commit()
    assert client.get(f"/atletas/{atleta_id}/atividades/{linha.atividade_id}").json()["carga"]["estado"] == "pendente"
    depois = client.get(f"/atletas/{atleta_id}/carga").json()["totais"]
    assert depois["pendentes"] == 1 and depois["calculadas"] == antes["totais"]["calculadas"] - 1
    soma = depois["calculadas"] + depois["sem_carga_total"] + depois["pendentes"] + depois["ignoradas_multiesporte"]
    assert soma == depois["atividades_importadas"]


def test_resposta_nao_vaza_saude(session, client):
    atleta_id = _atleta(session)
    j = client.get(f"/atletas/{atleta_id}/carga").json()
    assert set(j) == {"atleta_id", "versao", "versao_carga", "periodo", "aviso", "dias", "totais"}
    assert set(j["dias"][0]) == {"data", "carga", "ctl", "atl", "tsb", "aprendendo", "atividades", "calculadas", "sem_carga"}
    assert set(j["totais"]) == {"atividades_importadas", "calculadas", "sem_carga_total", "por_motivo",
                                "ignoradas_multiesporte", "pendentes"}
