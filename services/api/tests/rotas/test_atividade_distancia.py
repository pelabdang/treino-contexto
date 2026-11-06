"""`distancia` pronta em GET /atletas/{id}/atividades/{id} (issue #216, ADR 0004 adendo 3). Dados inventados."""

from datetime import datetime, timezone

import pytest
from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import criar_app
from app.rotas.atividades import distancia_da_atividade
from fastapi.testclient import TestClient

URL = "/atletas/{}/atividades/{}"


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


@pytest.mark.parametrize(
    "modalidade, metros, esperado",
    [
        ("corrida", 10000.0, "10,00 km"),
        ("ciclismo", 42195.0, "42,20 km"),
        ("corrida", 800.0, "0,80 km"),
        ("natacao", 1800.0, "1.800 m"),
        ("natacao", 750.4, "750 m"),
        ("natacao", 12000.0, "12.000 m"),
        ("corrida", 0.0, None),
        ("natacao", 0.0, None),
        ("corrida", None, None),
        ("natacao", None, None),
    ],
)
def test_distancia_da_atividade(modalidade, metros, esperado):
    assert distancia_da_atividade(modalidade, metros) == esperado


@pytest.mark.parametrize(
    "modalidade, metros, esperado",
    [("corrida", 10000.0, "10,00 km"), ("natacao", 1800.0, "1.800 m"), ("ciclismo", 0.0, None), ("corrida", None, None)],
)
def test_rota_manda_distancia_pronta(client, session, atleta, modalidade, metros, esperado):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id="1", modalidade=modalidade,
        inicio=datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc), duracao_s=3600.0, distancia_m=metros, fc_media=None,
    )
    session.add(a)
    session.commit()
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert j["distancia"] == esperado
    assert j["distancia_m"] == metros  # o numero antigo continua
