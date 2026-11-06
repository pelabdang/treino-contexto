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
    assert j["clima"] == {"estado": "ok", "temperatura_c": 24.3, "sensacao_c": 25.1, "umidade_pct": 61, "vento_kmh": 8.2,
                    "atribuicao": "Weather data by Open-Meteo.com"}


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


# --- Campos prontos para a tela (#158, ADR 0004 adendo 2). Contas feitas a mao. ---


def _ativ(session, atleta, n, **kw):
    base = dict(
        atleta_id=atleta.id, fonte="teste", fonte_id=f"p{n}", modalidade="corrida", subtipo=None,
        inicio=datetime(2025, 3, 5, 1, 30, tzinfo=timezone.utc), duracao_s=1800.0, distancia_m=5000.0,
        inicio_lat=LAT, inicio_lon=LON,
    )
    base.update(kw)
    a = Atividade(**base)
    session.add(a)
    session.commit()
    return a


def test_data_e_hora_locais_pelo_fuso_da_atividade(client, session, atleta):
    # 01:30 UTC com fuso -180 min = 22:30 do dia anterior
    a = _ativ(session, atleta, 1, fuso_min=-180)
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert (j["data_local"], j["hora_local"]) == ("2025-03-04", "22:30")
    assert j["inicio"].startswith("2025-03-05T01:30")  # UTC continua na resposta


def test_data_e_hora_locais_sem_fuso_usam_sao_paulo(client, session, atleta):
    a = _ativ(session, atleta, 2, fuso_min=None)
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert (j["data_local"], j["hora_local"]) == ("2025-03-04", "22:30")


def test_duracao_h_mm_ss_e_pace_m_ss(client, session, atleta):
    # 3725 s = 1:02:05; 3725 s / 10,5 km = 354,76 s/km -> 5:55
    a = _ativ(session, atleta, 3, duracao_s=3725.0, distancia_m=10500.0)
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert j["duracao"] == "1:02:05" and j["pace_medio"] == "5:55"


def test_duracao_curta_e_arredondamento(client, session, atleta):
    a = _ativ(session, atleta, 4, duracao_s=59.5, distancia_m=200.0)  # 1:00 ; 297,5 s/km -> 4:58
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert j["duracao"] == "0:01:00" and j["pace_medio"] == "4:58"


@pytest.mark.parametrize("modalidade,dist", [("natacao", 1000.0), ("ciclismo", 30000.0), ("corrida", None), ("corrida", 0.0)])
def test_pace_ausente_quando_nao_faz_sentido(client, session, atleta, modalidade, dist):
    a = _ativ(session, atleta, 5, modalidade=modalidade, distancia_m=dist)
    j = client.get(URL.format(atleta.id, a.id)).json()
    assert j["pace_medio"] is None


def test_atribuicao_so_com_clima_ok(client, session, atleta):
    a = _ativ(session, atleta, 6)
    _linha(session, a, "ok", temperatura_c=20.0, sensacao_c=20.0, umidade_pct=50, vento_kmh=5.0, fonte=FONTE_CLIMA)
    assert client.get(URL.format(atleta.id, a.id)).json()["clima"]["atribuicao"] == "Weather data by Open-Meteo.com"


def test_indoor_e_sem_posicao_nao_trazem_atribuicao(client, session, atleta):
    indoor = _ativ(session, atleta, 7, subtipo="esteira", inicio_lat=None, inicio_lon=None)
    sem = _ativ(session, atleta, 8, inicio_lat=None, inicio_lon=None)
    for a in (indoor, sem):
        j = client.get(URL.format(atleta.id, a.id)).json()
        assert "atribuicao" not in j["clima"] and "Open-Meteo" not in json.dumps(j)


def test_pendente_e_falha_nao_trazem_atribuicao(client, session, atleta):
    p = _ativ(session, atleta, 9)
    f = _ativ(session, atleta, 10)
    _linha(session, f, "falha", erro="x")
    for a in (p, f):
        assert "atribuicao" not in client.get(URL.format(atleta.id, a.id)).json()["clima"]


def test_openapi_campos_prontos_obrigatorios_e_pace_opcional(client):
    ativ = client.get("/openapi.json").json()["components"]["schemas"]["AtividadeOut"]
    for c in ("data_local", "hora_local", "duracao"):
        assert c in ativ["required"]
    assert "pace_medio" not in ativ["required"]
