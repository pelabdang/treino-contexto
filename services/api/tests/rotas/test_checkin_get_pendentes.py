"""`checkin` no GET da atividade e lista de pendentes (issue #298, ADR 0012), contra o oraculo das fixtures da Meta 8 (#294).

O que a `carga_pse` acrescenta no GET e da #297. Dados sinteticos; nada do check-in aparece na lista de pendentes.
"""

import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import get_session
from app.main import criar_app
from app.servicos import checkin as svc
from app.servicos.fuso import FUSO_PADRAO
from fastapi.testclient import TestClient

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta8"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta8_api", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


O = _oraculo()
ATIVIDADES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
CHECKINS = json.loads((PASTA / "checkins.json").read_text(encoding="utf-8"))
AGORA = datetime.fromisoformat(O.PARAMETROS["AGORA"])


def _hoje(instante: str) -> date:
    return datetime.fromisoformat(instante).astimezone(FUSO_PADRAO).date()


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: _hoje(O.PARAMETROS["AGORA"]))


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def banco(session):
    atleta, outro = Atleta(nome="Ana"), Atleta(nome="Beto")
    session.add_all([atleta, outro])
    session.flush()
    ids = {}
    for f in ATIVIDADES:
        a = Atividade(atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
                      inicio=datetime.fromisoformat(f["inicio"]), fuso_min=f["fuso_min"], duracao_s=f["duracao_s"])
        session.add(a)
        session.flush()
        ids[f["id"]] = a.id
        c = CHECKINS.get(f["id"])
        if c:
            session.add(CheckinTreino(
                atividade_id=a.id, pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"], texto=c["texto"],
                versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA, **{k: k in c["atalhos"] for k in
                                                                                  ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")}))
    session.commit()
    return atleta.id, outro.id, ids


def _get(client, banco, chave):
    atleta, _, ids = banco
    r = client.get(f"/atletas/{atleta}/atividades/{ids[chave]}")
    assert r.status_code == 200, r.text
    return r.json()


def _pendentes(client, banco, dias=None, agora=None, monkeypatch=None):
    atleta, _, ids = banco
    if agora:
        monkeypatch.setattr(svc, "hoje_local", lambda: _hoje(agora))
    r = client.get(f"/atletas/{atleta}/checkins/pendentes", params={"dias": dias} if dias else None)
    assert r.status_code == 200, r.text
    por_id = {v: k for k, v in ids.items()}
    return r.json(), [por_id[p["atividade_id"]] for p in r.json()["pendentes"]]


@pytest.mark.parametrize("agora,dias", sorted(O.PENDENTES))
def test_pendentes_igual_ao_oraculo(client, banco, monkeypatch, agora, dias):
    j, ids = _pendentes(client, banco, dias, agora, monkeypatch)
    assert ids == O.PENDENTES[(agora, dias)]  # mesma ordem: mais recentes primeiro
    assert j["dias"] == dias and j["total"] == len(ids)


def test_pendentes_padrao_e_7_dias(client, banco):
    j, ids = _pendentes(client, banco)
    assert j["dias"] == 7 and ids == O.PENDENTES[(O.PARAMETROS["AGORA"], 7)]


def test_pendentes_traz_so_campos_prontos_e_nenhum_do_checkin(client, banco):
    j, _ = _pendentes(client, banco)
    p = j["pendentes"][0]
    assert set(p) == {"atividade_id", "modalidade", "data_local", "hora_local", "duracao", "titulo"}
    assert (p["modalidade"], p["data_local"], p["hora_local"], p["duracao"], p["titulo"]) == (
        "corrida", "2026-11-05", "07:00", "0:45:00", "Corrida, 45 min")
    texto = json.dumps(j)
    assert "pse" not in texto and "sensacao" not in texto and "atalho" not in texto


def test_pendentes_nao_traz_pai_nem_troca_mas_traz_subtipo_nulo(client, banco):
    _, ids = _pendentes(client, banco)
    assert not any(i.split("/")[1].startswith("out") for i in ids)  # pai e trocas
    assert "2026-11-04/cic1" in ids  # subtipo nulo continua (o NOT IN solto o excluiria)


def test_pendentes_so_do_atleta(client, banco):
    _, outro, _ = banco
    r = client.get(f"/atletas/{outro}/checkins/pendentes")
    assert r.status_code == 200 and r.json() == {"dias": 7, "total": 0, "pendentes": []}


def test_pendentes_cai_quando_o_checkin_e_feito(client, banco):
    atleta, _, ids = banco
    r = client.put(f"/atletas/{atleta}/atividades/{ids['2026-11-05/cor1']}/checkin",
                   json={"pse": 5, "sensacao": 3, "nada_a_relatar": True})
    assert r.status_code == 200
    _, pend = _pendentes(client, banco)
    assert "2026-11-05/cor1" not in pend


@pytest.mark.parametrize("dias", [0, 8, -1, "x"])
def test_pendentes_422_para_dias_fora_de_1_a_7_sem_eco(client, banco, dias):
    atleta, _, _ = banco
    r = client.get(f"/atletas/{atleta}/checkins/pendentes", params={"dias": dias})
    assert r.status_code == 422
    assert all(set(e) == {"loc", "msg", "type"} for e in r.json()["detail"]) and "input" not in r.text


def test_pendentes_404_atleta_inexistente(client, banco):
    assert client.get("/atletas/999/checkins/pendentes").status_code == 404


def test_get_da_atividade_traz_o_checkin(client, banco):
    j = _get(client, banco, "2026-11-09/cor2")
    c = j["checkin"]
    assert (c["pse"], c["pse_texto"], c["sensacao"], c["sensacao_texto"], c["nada_a_relatar"]) == (6, "6", 4, "bem", False)
    assert [a["chave"] for a in c["atalhos"]] == ["cansaco", "trabalho_estresse"] and c["texto"] == "Semana puxada no trabalho."
    assert j["checkin_aberto"] is True


def test_get_da_atividade_sem_checkin_vem_null(client, banco):
    j = _get(client, banco, "2026-11-05/cor1")
    assert j["checkin"] is None and j["checkin_aberto"] is True and j["pse_sugerida"] is None


@pytest.mark.parametrize("chave", sorted(k for k, v in O.PRAZO_CRIAR.items() if v is not None))
def test_checkin_aberto_segue_o_prazo_do_oraculo(client, banco, chave):
    assert _get(client, banco, chave)["checkin_aberto"] is O.PRAZO_CRIAR[chave]


@pytest.mark.parametrize("chave", sorted(O.NAO_ELEGIVEIS))
def test_pai_e_troca_nao_tem_checkin_aberto_nem_checkin(client, banco, chave):
    j = _get(client, banco, chave)
    assert j["checkin"] is None and j["checkin_aberto"] is False and j["pse_sugerida"] is None


def test_checkin_existente_fora_do_prazo_continua_aberto_para_editar(client, banco):
    j = _get(client, banco, "2026-10-15/cor1")  # 25 dias antes, com check-in
    assert j["checkin"]["pse"] == 5 and j["checkin_aberto"] is True


def test_pse_sugerida_e_a_da_parte_anterior_do_mesmo_multiesporte(client, banco):
    # 03/11: pai 10:55, natacao 11:00 (PSE 5), troca, ciclismo 11:33 (PSE 6), troca, corrida 12:20 (sem check-in)
    assert _get(client, banco, "2026-11-03/nat1")["pse_sugerida"] is None  # primeira parte
    assert _get(client, banco, "2026-11-03/cic1")["pse_sugerida"] == 5  # a natacao (a troca no meio nao conta)
    assert _get(client, banco, "2026-11-03/cor1")["pse_sugerida"] == 6  # o ciclismo
    assert _get(client, banco, "2026-11-08/cic1")["pse_sugerida"] is None  # treino avulso


def test_pse_sugerida_nula_quando_a_parte_anterior_nao_tem_checkin(client, banco, session):
    atleta, _, ids = banco
    session.delete(session.get(CheckinTreino, session.query(CheckinTreino).filter_by(atividade_id=ids["2026-11-03/cic1"]).one().id))
    session.commit()
    assert _get(client, banco, "2026-11-03/cor1")["pse_sugerida"] is None


def test_checkin_de_outro_atleta_nao_vaza(client, banco):
    atleta, outro, ids = banco
    assert client.get(f"/atletas/{outro}/atividades/{ids['2026-11-09/cor2']}").status_code == 404


def test_campos_antigos_do_get_continuam(client, banco):
    j = _get(client, banco, "2026-11-09/cor2")
    for campo in ("atividade_id", "clima", "esforcos", "carga", "linha_base", "tipo_treino", "data_local", "pace_medio"):
        assert campo in j
