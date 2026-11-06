"""Treino de transicao pela API: listar, comparar e corrigir (issue #170, ADR 0009). Dados inventados; contas feitas a mao."""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta, RotuloTransicao
from app.db.session import get_session
from app.main import criar_app
from app.servicos.transicao import aplicar_sugestao
from fastapi.testclient import TestClient

BASE = "/atletas/{}/treinos-de-transicao"
URL_ATIV = "/atletas/{}/atividades/{}"
URL_TRANS = "/atletas/{}/atividades/{}/transicao"


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


def _ativ(session, atleta, n, modalidade, inicio, dur, dist, fc):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id=str(n), modalidade=modalidade, inicio=inicio,
        duracao_s=dur, distancia_m=dist, fc_media=fc, fuso_min=-180,
    )
    session.add(a)
    session.commit()
    return a


def utc(dia, h, m=0):
    return datetime(2025, 3, dia, h, m, tzinfo=timezone.utc)


@pytest.fixture
def dois_bricks(session, atleta):
    """A (dia 4): ciclismo 10:00 3600 s 30 km fc 140; corrida 11:02 (intervalo 120 s) 1500 s 5 km fc 160.
    B (dia 6): ciclismo 10:00 3300 s 25 km fc 150; corrida 10:58 (intervalo 180 s) 1380 s 5 km fc 170."""
    a1 = _ativ(session, atleta, 1, "ciclismo", utc(4, 10), 3600, 30000, 140)
    a2 = _ativ(session, atleta, 2, "corrida", utc(4, 11, 2), 1500, 5000, 160)
    b1 = _ativ(session, atleta, 3, "ciclismo", utc(6, 10), 3300, 25000, 150)
    b2 = _ativ(session, atleta, 4, "corrida", utc(6, 10, 58), 1380, 5000, 170)
    aplicar_sugestao(session, atleta.id)
    return a1, a2, b1, b2


def test_lista_com_partes_e_intervalo_a_mao(client, atleta, dois_bricks):
    a1, a2, b1, b2 = dois_bricks
    r = client.get(BASE.format(atleta.id))
    assert r.status_code == 200
    j = r.json()
    assert "periodo" not in j
    assert [g["grupo_id"] for g in j["grupos"]] == [b1.id, a1.id]  # mais recente primeiro
    g = j["grupos"][1]
    assert g["forma"] == "ciclismo>corrida" and g["incompleto"] is False
    assert g["data_local"] == "2025-03-04" and g["hora_local"] == "07:00"  # fuso -180
    c, k = g["partes"]
    assert (c["ordem"], c["modalidade"], c["duracao"], c["distancia"], c["fc_media"]) == (1, "ciclismo", "1:00:00", "30,00 km", 140.0)
    assert (c["ritmo_valor"], c["ritmo_unidade"], c["ritmo"]) == (30.0, "km/h", "30,0 km/h")
    assert (k["modalidade"], k["duracao"], k["distancia"], k["fc_media"]) == ("corrida", "0:25:00", "5,00 km", 160.0)
    assert (k["ritmo_valor"], k["ritmo_unidade"], k["ritmo"]) == (300.0, "s/km", "5:00 /km")
    assert g["transicoes"] == [
        {"de_atividade_id": a1.id, "para_atividade_id": a2.id, "intervalo_estimado_s": 120.0, "intervalo_estimado": "2:00"}
    ]
    assert (g["soma_duracoes_s"], g["soma_duracoes"]) == (5100.0, "1:25:00")
    assert (g["soma_intervalos_estimados_s"], g["soma_intervalos_estimados"]) == (120.0, "2:00")
    assert (g["tempo_total_s"], g["tempo_total"]) == (5220.0, "1:27:00")
    assert g["fc_media"] == 145.9  # (140*3600 + 160*1500) / 5100


def test_filtro_de_periodo_pela_data_local(client, atleta, dois_bricks):
    j = client.get(BASE.format(atleta.id), params={"inicio": "2025-03-05"}).json()
    assert [g["data_local"] for g in j["grupos"]] == ["2025-03-06"]
    assert j["periodo"] == {"inicio": "2025-03-05", "fim": None}
    assert client.get(BASE.format(atleta.id), params={"inicio": "2025-03-05", "fim": "2025-03-05"}).json()["grupos"] == []
    assert client.get(BASE.format(atleta.id), params={"inicio": "2025-03-06", "fim": "2025-03-05"}).status_code == 422


def test_intervalo_nunca_negativo(client, session, atleta):
    _ativ(session, atleta, 1, "ciclismo", utc(4, 10), 3600, 30000, None)
    _ativ(session, atleta, 2, "corrida", utc(4, 10, 59, ) + timedelta(seconds=30), 1500, 5000, None)  # abre 30 s antes
    aplicar_sugestao(session, atleta.id)
    g = client.get(BASE.format(atleta.id)).json()["grupos"][0]
    assert g["transicoes"][0]["intervalo_estimado_s"] == 0.0 and g["soma_intervalos_estimados"] == "0:00"
    assert g["fc_media"] is None


def test_comparar_mesma_forma(client, atleta, dois_bricks):
    a1, _, b1, _ = dois_bricks
    r = client.get(BASE.format(atleta.id) + "/comparar", params={"a": a1.id, "b": b1.id})
    assert r.status_code == 200
    j = r.json()
    assert j["forma"] == "ciclismo>corrida" and j["a"]["grupo_id"] == a1.id and j["b"]["grupo_id"] == b1.id
    ciclismo, corrida = j["partes"]
    assert (ciclismo["duracao_dif_s"], ciclismo["duracao_dif"]) == (-300.0, "-5:00")
    assert (ciclismo["ritmo_dif"], ciclismo["ritmo_dif_texto"]) == (-2.7, "-2,7 km/h")  # 27,27 - 30
    assert (corrida["duracao_dif"], corrida["ritmo_dif"], corrida["ritmo_dif_texto"]) == ("-2:00", -24.0, "-0:24 /km")
    assert (corrida["fc_dif"], corrida["fc_dif_texto"]) == (10.0, "+10 bpm")
    t = j["total"]
    assert t["soma_duracoes_dif"] == "-7:00"  # 4680 - 5100
    assert t["soma_intervalos_estimados_dif"] == "+1:00"  # 180 - 120
    assert t["tempo_total_dif"] == "-6:00"  # 4860 - 5220
    assert (t["fc_dif"], t["fc_dif_texto"]) == (10.0, "+10 bpm")  # 155,9 - 145,9


def test_comparar_formas_diferentes_da_400(client, session, atleta, dois_bricks):
    a1, *_ = dois_bricks
    n = _ativ(session, atleta, 10, "natacao", utc(8, 9), 1800, 1800, 130)
    _ativ(session, atleta, 11, "ciclismo", utc(8, 9, 35), 3000, 20000, 140)
    aplicar_sugestao(session, atleta.id)
    r = client.get(BASE.format(atleta.id) + "/comparar", params={"a": a1.id, "b": n.id})
    assert r.status_code == 400
    assert r.json()["detail"] == (
        "só se comparam treinos da mesma sequência de modalidades: a é ciclismo>corrida e b é natacao>ciclismo"
    )
    nat = client.get(BASE.format(atleta.id)).json()["grupos"][0]["partes"][0]
    assert (nat["distancia"], nat["ritmo"]) == ("1.800 m", "1:40 /100 m")  # 1800 s / 1800 m * 100 = 100 s/100 m


def test_comparar_404(client, session, atleta, dois_bricks):
    a1, a2, *_ = dois_bricks
    url = BASE.format(atleta.id) + "/comparar"
    assert client.get(url, params={"a": a1.id, "b": 9999}).status_code == 404
    assert client.get(url, params={"a": a1.id, "b": a2.id}).status_code == 404  # a2 e parte, nao e o grupo_id
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    assert client.get(BASE.format(outro.id) + "/comparar", params={"a": a1.id, "b": a1.id}).status_code == 404
    assert client.get(BASE.format(999) + "/comparar", params={"a": 1, "b": 1}).json() == {"detail": "atleta não encontrado"}
    assert client.get(BASE.format(999)).status_code == 404


def test_corrigir_para_nao_tira_da_lista_e_a_regra_nao_devolve(client, session, atleta, dois_bricks):
    a1, a2, b1, b2 = dois_bricks
    for x in (b1, b2):
        r = client.put(URL_TRANS.format(atleta.id, x.id), json={"transicao": False})
        assert r.status_code == 200 and r.json() == {"valor": False, "origem": "atleta"}
    grupos = client.get(BASE.format(atleta.id)).json()["grupos"]
    assert [g["grupo_id"] for g in grupos] == [a1.id]
    rel = aplicar_sugestao(session, atleta.id)  # a regra roda de novo
    assert rel.do_atleta == 2
    assert [g["grupo_id"] for g in client.get(BASE.format(atleta.id)).json()["grupos"]] == [a1.id]
    assert client.get(URL_ATIV.format(atleta.id, b1.id)).json()["transicao"] == {"valor": False, "origem": "atleta"}


def test_nao_so_numa_parte_deixa_a_outra_incompleta(client, atleta, dois_bricks):
    _, _, b1, b2 = dois_bricks
    client.put(URL_TRANS.format(atleta.id, b2.id), json={"transicao": False})
    g = client.get(BASE.format(atleta.id)).json()["grupos"][0]
    assert g["grupo_id"] == b1.id and g["incompleto"] is True and g["transicoes"] == [] and g["forma"] == "ciclismo"


def test_sim_avulso_aparece_incompleto(client, session, atleta):
    solta = _ativ(session, atleta, 1, "corrida", utc(4, 10), 1800, 5000, 150)
    assert client.get(URL_ATIV.format(atleta.id, solta.id)).json()["transicao"] == {"valor": False, "origem": None}
    r = client.put(URL_TRANS.format(atleta.id, solta.id), json={"transicao": True})
    assert r.json() == {"valor": True, "origem": "atleta"}
    g = client.get(BASE.format(atleta.id)).json()["grupos"][0]
    assert g["incompleto"] is True and g["forma"] == "corrida" and len(g["partes"]) == 1
    row = session.query(RotuloTransicao).one()
    assert (row.transicao, row.origem, row.versao_regra) == (True, "atleta", None)


def test_put_troca_a_linha_sugerida_pela_do_atleta(client, session, atleta, dois_bricks):
    a1, *_ = dois_bricks
    assert client.get(URL_ATIV.format(atleta.id, a1.id)).json()["transicao"] == {"valor": True, "origem": "sugerido"}
    client.put(URL_TRANS.format(atleta.id, a1.id), json={"transicao": True})
    session.expire_all()
    row = session.query(RotuloTransicao).filter_by(atividade_id=a1.id).one()
    assert (row.origem, row.versao_regra) == ("atleta", None)


def test_delete_desfaz_so_a_correcao_do_atleta(client, session, atleta, dois_bricks):
    a1, a2, *_ = dois_bricks
    client.put(URL_TRANS.format(atleta.id, a1.id), json={"transicao": False})
    r = client.delete(URL_TRANS.format(atleta.id, a1.id))
    assert r.status_code == 204 and r.content == b""
    assert client.get(URL_ATIV.format(atleta.id, a1.id)).json()["transicao"] == {"valor": False, "origem": None}
    aplicar_sugestao(session, atleta.id)  # a regra volta a valer
    assert client.get(URL_ATIV.format(atleta.id, a1.id)).json()["transicao"] == {"valor": True, "origem": "sugerido"}
    # DELETE sobre linha sugerida (ou sem linha) e 204 e nao apaga nada
    assert client.delete(URL_TRANS.format(atleta.id, a1.id)).status_code == 204
    assert client.get(URL_ATIV.format(atleta.id, a1.id)).json()["transicao"] == {"valor": True, "origem": "sugerido"}


def test_put_e_delete_404_e_422(client, session, atleta, dois_bricks):
    a1, *_ = dois_bricks
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    for metodo, corpo in (("put", {"json": {"transicao": True}}), ("delete", {})):
        f = getattr(client, metodo)
        assert f(URL_TRANS.format(999, a1.id), **corpo).json() == {"detail": "atleta não encontrado"}
        assert f(URL_TRANS.format(atleta.id, 9999), **corpo).json() == {"detail": "atividade não encontrada"}
        assert f(URL_TRANS.format(outro.id, a1.id), **corpo).status_code == 404  # atividade de outro atleta
    assert client.put(URL_TRANS.format(atleta.id, a1.id), json={"transicao": "talvez"}).status_code == 422
    assert client.put(URL_TRANS.format(atleta.id, a1.id), json={}).status_code == 422
    assert session.query(RotuloTransicao).filter_by(origem="atleta").count() == 0
