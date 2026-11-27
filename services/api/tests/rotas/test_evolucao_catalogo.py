"""`GET /atletas/{id}/evolucao/series`: o catálogo de séries (issue #573). Dados inventados; valores contados à mão."""

from datetime import datetime, time, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import criar_app
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.acesso_de_teste import sem_login

HOJE = datetime.now(timezone.utc).date()


@pytest.fixture
def client(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    return TestClient(sem_login(a))


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


_n = iter(range(1, 10_000))


def _ativ(session, atleta, dias_atras, modalidade="corrida", tipo="leve", fc=150.0, dur=1800.0, dist=5000.0, subtipo=None):
    inicio = datetime.combine(HOJE - timedelta(days=dias_atras), time(12, 0), tzinfo=timezone.utc)
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=str(next(_n)), modalidade=modalidade, subtipo=subtipo, inicio=inicio, fuso_min=0,
                  duracao_s=dur, distancia_m=dist, fc_media=fc, tipo_treino=tipo)
    session.add(a)
    session.flush()
    return a


def _get(client, atleta):
    r = client.get(f"/atletas/{atleta.id}/evolucao/series")
    assert r.status_code == 200
    return r.json()


def _por_id(j):
    return {s["id"]: s for s in j["series"]}


def test_atleta_sem_treino_nao_tem_serie(client, atleta):
    assert _get(client, atleta) == {"atleta_id": atleta.id, "series": [], "serie_padrao": None}


def test_404_atleta_inexistente(client):
    assert client.get("/atletas/9999/evolucao/series").status_code == 404


def test_so_as_series_que_o_atleta_tem(client, session, atleta):
    for d in range(1, 10):  # 9 corridas leves, uma por dia
        _ativ(session, atleta, d)
    j = _get(client, atleta)
    ids = [s["id"] for s in j["series"]]
    assert ids == ["corrida.pace.leve", "corrida.fc.leve", "corrida.volume_km", "corrida.volume_h"]  # modalidade, grupo, ordem do catálogo
    s = _por_id(j)["corrida.pace.leve"]
    assert s == {"id": "corrida.pace.leve", "titulo": "Pace dos treinos leves", "descricao": "O pace médio de cada treino leve de corrida",
                 "modalidade": "corrida", "grupo": "Ritmo", "n_pontos": 9, "disponivel": True, "motivo": None}
    assert _por_id(j)["corrida.fc.leve"]["grupo"] == "Coração"
    assert j["serie_padrao"] == "corrida.pace.leve"  # a do último treino


def test_poucos_pontos_vira_indisponivel_com_motivo(client, session, atleta):
    for d in (1, 2):
        _ativ(session, atleta, d)
    s = _por_id(_get(client, atleta))["corrida.pace.leve"]
    assert s["n_pontos"] == 2 and s["disponivel"] is False
    assert s["motivo"] == "Poucos treinos leves de corrida nas últimas 12 semanas"


def test_tres_em_cada_janela_basta_mesmo_com_menos_de_8(client, session, atleta):
    # R = 1..28 dias atrás; A = 29..56. 3 em cada = 6 pontos (< 8).
    for d in (1, 10, 20, 30, 40, 50):
        _ativ(session, atleta, d)
    s = _por_id(_get(client, atleta))["corrida.pace.leve"]
    assert s["n_pontos"] == 6 and s["disponivel"] is True


def test_hoje_nao_conta_na_janela_da_frase(client, session, atleta):
    # R termina ontem: o treino de hoje não é da janela. 2 em R (1, 10) + hoje; 3 em A; 6 pontos no total.
    for d in (0, 1, 10, 30, 40, 50):
        _ativ(session, atleta, d)
    assert _por_id(_get(client, atleta))["corrida.pace.leve"]["disponivel"] is False


def test_treino_antigo_fora_das_12_semanas_nao_conta_pontos(client, session, atleta):
    for d in (100, 120, 150, 5):
        _ativ(session, atleta, d)
    s = _por_id(_get(client, atleta))["corrida.pace.leve"]
    assert s["n_pontos"] == 1 and s["disponivel"] is False


def test_esteira_fora_do_pace_mas_dentro_da_fc_e_do_volume(client, session, atleta):
    for d in range(1, 10):
        _ativ(session, atleta, d, subtipo="esteira")
    por = _por_id(_get(client, atleta))
    assert "corrida.pace.leve" not in por
    assert por["corrida.fc.leve"]["n_pontos"] == 9
    assert "corrida.volume_km" in por  # a esteira conta no volume


def test_sem_fc_nao_conta_na_serie_de_fc(client, session, atleta):
    for d in range(1, 10):
        _ativ(session, atleta, d, fc=None if d <= 5 else 150.0)
    por = _por_id(_get(client, atleta))
    assert por["corrida.fc.leve"]["n_pontos"] == 4 and por["corrida.fc.leve"]["disponivel"] is False
    assert por["corrida.pace.leve"]["n_pontos"] == 9


def test_volume_conta_semanas_com_treino(client, session, atleta):
    for sem in range(5):  # uma corrida por semana, 5 semanas seguidas
        _ativ(session, atleta, 3 + 7 * sem, tipo=None)
    por = _por_id(_get(client, atleta))
    assert por["corrida.volume_km"]["n_pontos"] == 5 and por["corrida.volume_km"]["disponivel"] is True
    assert "corrida.pace.leve" not in por  # sem tipo, fora das séries por tipo
    assert por["corrida.volume_km"]["motivo"] is None


def test_volume_com_duas_semanas_e_indisponivel(client, session, atleta):
    _ativ(session, atleta, 3, tipo=None)
    _ativ(session, atleta, 10, tipo=None)
    s = _por_id(_get(client, atleta))["corrida.volume_km"]
    assert s["n_pontos"] == 2 and s["disponivel"] is False
    assert s["motivo"] == "Poucas semanas com corrida nas últimas 12 semanas"


def test_natacao_ritmo_so_na_piscina(client, session, atleta):
    for d in range(1, 10):
        _ativ(session, atleta, d, modalidade="natacao", tipo=None, subtipo="piscina" if d % 2 else "aguas_abertas", dist=1000.0)
    por = _por_id(_get(client, atleta))
    assert por["natacao.ritmo"]["n_pontos"] == 5 and por["natacao.ritmo"]["modalidade"] == "natacao"
    assert por["natacao.fc"]["n_pontos"] == 9
    assert not any(i.startswith("corrida") for i in por)


def test_ciclismo_separa_na_rua_e_em_casa(client, session, atleta):
    for d in range(1, 9):
        _ativ(session, atleta, d, modalidade="ciclismo", tipo=None, subtipo=None, dist=30000.0)
    _ativ(session, atleta, 3, modalidade="ciclismo", tipo=None, subtipo="virtual", dist=30000.0)
    _ativ(session, atleta, 4, modalidade="ciclismo", tipo=None, subtipo="esteira", dist=30000.0)  # rolo
    por = _por_id(_get(client, atleta))
    assert por["ciclismo.velocidade.rua"]["n_pontos"] == 8 and por["ciclismo.velocidade.rua"]["disponivel"] is True
    assert por["ciclismo.velocidade.casa"]["n_pontos"] == 2 and por["ciclismo.velocidade.casa"]["disponivel"] is False  # virtual + rolo juntos
    assert por["ciclismo.velocidade.casa"]["titulo"] == "Velocidade em casa" and por["ciclismo.fc.rua"]["titulo"] == "FC no pedal na rua"
    assert not any(i.endswith(("ar_livre", "virtual", "rolo")) for i in por)


def test_multiesporte_pai_e_troca_ficam_fora(client, session, atleta):
    for d in range(1, 10):
        _ativ(session, atleta, d, subtipo="multiesporte_pai")
    assert _get(client, atleta)["series"] == []


def test_outro_atleta_nao_entra(client, session, atleta):
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    for d in range(1, 10):
        _ativ(session, outro, d)
    assert _get(client, atleta)["series"] == []


def test_numero_de_consultas_nao_cresce_com_as_series(client, session, atleta):
    for d in range(1, 30):
        _ativ(session, atleta, d, tipo=("leve", "moderado", "longo")[d % 3])
        _ativ(session, atleta, d, modalidade="ciclismo", tipo=None, subtipo=(None, "virtual", "esteira")[d % 3])
        _ativ(session, atleta, d, modalidade="natacao", tipo=None, subtipo="piscina")
    session.commit()
    n = []
    event.listen(session.get_bind(), "before_cursor_execute", lambda *a: n.append(1))
    assert len(_get(client, atleta)["series"]) >= 15
    assert len(n) <= 8


def test_openapi_descreve_o_catalogo(client):
    esquema = client.get("/openapi.json").json()
    assert "/atletas/{atleta_id}/evolucao/series" in esquema["paths"]
    s = esquema["components"]["schemas"]["SerieCatalogoOut"]
    assert {"id", "titulo", "descricao", "modalidade", "grupo", "n_pontos", "disponivel", "motivo"} <= set(s["required"])
