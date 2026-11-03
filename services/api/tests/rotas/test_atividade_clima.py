"""GET /atletas/{id}/atividades/{id} com o objeto `clima` (issue #114, ADR 0007 item 5). Dados inventados."""

import json
from datetime import datetime, timezone

import pytest
from app.db.models import Atividade, Atleta, ClimaAtividade
from app.db.session import get_session
from app.main import criar_app
from app.servicos.clima import FONTE_CLIMA, entrada_de
from fastapi.testclient import TestClient

URL = "/atletas/{}/atividades/{}"
LAT, LON = -23.55, -46.63  # posicao inventada, arredondada
VALORES = {"temperatura_c", "sensacao_c", "umidade_pct", "vento_kmh"}


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


def _atividade(session, atleta, n, *, subtipo=None, posicao=True):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id=str(n), modalidade="corrida", subtipo=subtipo,
        inicio=datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc), duracao_s=1800.0, distancia_m=5000.0, fc_media=150.0,
        inicio_lat=LAT if posicao else None, inicio_lon=LON if posicao else None,
    )
    session.add(a)
    session.commit()
    return a


def _linha(session, a, estado, **extra):
    session.add(ClimaAtividade(atividade_id=a.id, estado=estado, entrada=entrada_de(a), **extra))
    session.commit()


def test_clima_ok_com_os_quatro_valores(client, session, atleta):
    a = _atividade(session, atleta, 1)
    _linha(session, a, "ok", temperatura_c=24.3, sensacao_c=25.1, umidade_pct=61, vento_kmh=8.2, fonte=FONTE_CLIMA)
    r = client.get(URL.format(atleta.id, a.id))
    assert r.status_code == 200
    j = r.json()
    assert j["atividade_id"] == a.id and j["modalidade"] == "corrida" and j["distancia_m"] == 5000.0
    assert j["clima"] == {"estado": "ok", "temperatura_c": 24.3, "sensacao_c": 25.1, "umidade_pct": 61, "vento_kmh": 8.2}


def test_clima_indoor(client, session, atleta):
    a = _atividade(session, atleta, 2, subtipo="esteira", posicao=False)
    assert client.get(URL.format(atleta.id, a.id)).json()["clima"] == {"estado": "indoor"}


def test_clima_sem_posicao(client, session, atleta):
    a = _atividade(session, atleta, 3, posicao=False)
    assert client.get(URL.format(atleta.id, a.id)).json()["clima"] == {"estado": "sem_posicao"}


def test_clima_pendente_sem_linha(client, session, atleta):
    a = _atividade(session, atleta, 4)
    assert client.get(URL.format(atleta.id, a.id)).json()["clima"] == {"estado": "pendente"}


def test_clima_pendente_com_linha_pendente(client, session, atleta):
    a = _atividade(session, atleta, 5)
    _linha(session, a, "pendente", tentativas=1)
    assert client.get(URL.format(atleta.id, a.id)).json()["clima"] == {"estado": "pendente"}


def test_clima_falha_nao_vaza_o_erro(client, session, atleta):
    a = _atividade(session, atleta, 6)
    _linha(session, a, "falha", tentativas=1, erro="HTTP 500 interno")
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert j["clima"] == {"estado": "falha"}
    assert "interno" not in json.dumps(j)


def test_valores_so_aparecem_em_ok(client, session, atleta):
    a = _atividade(session, atleta, 7)
    _linha(session, a, "falha", temperatura_c=1.0)  # lixo na linha nao pode aparecer
    assert VALORES.isdisjoint(client.get(URL.format(atleta.id, a.id)).json()["clima"])


def test_404_atleta_inexistente(client):
    r = client.get(URL.format(999, 1))
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}


def test_404_atividade_inexistente(client, atleta):
    r = client.get(URL.format(atleta.id, 999))
    assert r.status_code == 404 and r.json() == {"detail": "atividade não encontrada"}


def test_404_atividade_de_outro_atleta(client, session, atleta):
    outro = Atleta(nome="Outra Ficticia")
    session.add(outro)
    session.commit()
    a = _atividade(session, outro, 8)
    assert client.get(URL.format(atleta.id, a.id)).status_code == 404
    assert client.get(URL.format(outro.id, a.id)).status_code == 200


def test_nunca_expoe_a_posicao_na_resposta(client, session, atleta):
    a = _atividade(session, atleta, 9)
    _linha(session, a, "ok", temperatura_c=20.0, sensacao_c=20.0, umidade_pct=50, vento_kmh=5.0)
    texto = client.get(URL.format(atleta.id, a.id)).text
    assert "inicio_lat" not in texto and "inicio_lon" not in texto
    assert str(LAT) not in texto and str(LON) not in texto


def test_openapi_tem_clima_opcional_e_sem_posicao(client):
    doc = client.get("/openapi.json").json()
    assert "inicio_lat" not in json.dumps(doc) and "inicio_lon" not in json.dumps(doc)
    esquemas = doc["components"]["schemas"]
    ativ, clima = esquemas["AtividadeOut"], esquemas["ClimaOut"]
    assert "clima" in ativ["properties"] and "clima" not in ativ.get("required", [])
    assert clima["properties"]["estado"]["enum"] == ["ok", "indoor", "sem_posicao", "pendente", "falha"]
    assert clima["required"] == ["estado"]
    op = doc["paths"]["/atletas/{atleta_id}/atividades/{atividade_id}"]["get"]
    assert op["operationId"] == "buscarAtividade" and "404" in op["responses"]
