"""`checkin`, `carga_pse`, `checkin_aberto` e `pse_sugerida` no GET da atividade e lista de pendentes (issue #298, ADR 0012), contra o
oraculo inteiro das fixtures da Meta 8 (#294): `CARGA_PSE_ESPERADA` (18 atividades), `PRAZO_CRIAR`, `PENDENTES`, `NAO_ELEGIVEIS` e
`VALIDACAO` (21 corpos do PUT), passando pelo banco e pela API.

Dados sinteticos; nada do check-in aparece na lista de pendentes nem no log (marcador sintetico e `caplog`).
"""

import importlib.util
import json
import logging
import sys
from datetime import date, datetime
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
    _, _, ids = banco
    session.delete(session.get(CheckinTreino, session.query(CheckinTreino).filter_by(atividade_id=ids["2026-11-03/cic1"]).one().id))
    session.commit()
    assert _get(client, banco, "2026-11-03/cor1")["pse_sugerida"] is None


def test_checkin_de_outro_atleta_nao_vaza(client, banco):
    _, outro, ids = banco
    assert client.get(f"/atletas/{outro}/atividades/{ids['2026-11-09/cor2']}").status_code == 404


def test_campos_antigos_do_get_continuam(client, banco):
    j = _get(client, banco, "2026-11-09/cor2")
    for campo in ("atividade_id", "clima", "esforcos", "carga", "linha_base", "tipo_treino", "data_local", "pace_medio"):
        assert campo in j


# --- carga_pse@1 no GET, as 18 atividades do oraculo (ADR 0012, itens 6 e 7) -----------------------------------------------


@pytest.mark.parametrize("chave", sorted(O.CARGA_PSE_ESPERADA))
def test_carga_pse_do_get_igual_ao_oraculo(client, banco, chave):
    esperado = O.CARGA_PSE_ESPERADA[chave]
    c = _get(client, banco, chave)["carga_pse"]
    if esperado is None:  # pai e troca
        assert c is None
        return
    estado, minutos, valor = esperado
    assert (c["versao"], c["estado"]) == ("carga_pse@1", estado)
    assert c["minutos"] == pytest.approx(minutos)
    if valor is None:
        assert c["valor"] is None and c["valor_texto"] is None
    else:
        assert c["valor"] == pytest.approx(valor) and c["valor_texto"].endswith(" UA")
    assert (c["pse"] is None) is (estado == "sem_checkin")
    assert set(c) == {"versao", "estado", "pse", "minutos", "valor", "valor_texto", "texto"}  # nunca a observacao nem a sensacao


@pytest.mark.parametrize("chave,valor_texto,texto", [
    ("2026-11-09/cor2", "270 UA", "Carga pela PSE: 6 x 45 min = 270 UA."),
    ("2026-11-07/cor1", "272,5 UA", "Carga pela PSE: 6 x 45 min 25 s = 272,5 UA."),  # 2725 s: minutos e segundos quando nao e inteiro
    ("2026-11-08/nat1", "160 UA", "Carga pela PSE: 4 x 40 min = 160 UA."),  # natacao tem carga pela PSE
    ("2026-11-08/cic1", "350 UA", "Carga pela PSE: 7 x 50 min = 350 UA."),
    ("2026-11-06/out1", "0 UA", "Carga pela PSE: 0 x 30 min = 0 UA."),  # PSE 0 vale
    ("2026-11-05/cor1", None, "Sem check-in: a carga pela PSE precisa da PSE do treino."),
    ("2026-11-09/cor1", None, "Treino sem duração registrada: sem carga pela PSE."),
])
def test_carga_pse_textos_prontos(client, banco, chave, valor_texto, texto):
    c = _get(client, banco, chave)["carga_pse"]
    assert (c["valor_texto"], c["texto"]) == (valor_texto, texto)


def test_carga_pse_separada_da_carga_do_relogio(client, banco):
    j = _get(client, banco, "2026-11-08/nat1")
    assert j["carga_pse"]["estado"] == "calculada"  # natacao: tem carga pela PSE...
    assert j["carga"] is None or j["carga"]["estado"] != "calculada"  # ...e nao a carga@2


def test_carga_pse_acompanha_o_checkin(client, banco):
    atleta, _, ids = banco
    url = f"/atletas/{atleta}/atividades/{ids['2026-11-05/cor1']}/checkin"
    assert client.put(url, json={"pse": 8, "sensacao": 2, "nada_a_relatar": True}).status_code == 200
    c = _get(client, banco, "2026-11-05/cor1")["carga_pse"]
    assert (c["estado"], c["pse"], c["valor"]) == ("calculada", 8, 360.0)  # 8 x 45
    assert client.delete(url).status_code == 204
    assert _get(client, banco, "2026-11-05/cor1")["carga_pse"]["estado"] == "sem_checkin"


# --- prazo de criacao pelo PUT, as atividades sem check-in do oraculo (ADR 0012, itens 3 e 4) ------------------------------


@pytest.mark.parametrize("chave", sorted(O.PRAZO_CRIAR))
def test_prazo_de_criar_pelo_put_igual_ao_oraculo(client, banco, session, chave):
    atleta, _, ids = banco
    r = client.put(f"/atletas/{atleta}/atividades/{ids[chave]}/checkin", json={"pse": 5, "sensacao": 3, "nada_a_relatar": True})
    esperado = O.PRAZO_CRIAR[chave]
    if esperado is True:
        assert r.status_code == 200, r.text
        assert _get(client, banco, chave)["checkin"]["pse"] == 5
    else:
        assert r.status_code == 422
        assert r.json()["detail"][0]["type"] == ("fora_do_prazo" if esperado is False else "atividade_sem_checkin")
        assert _get(client, banco, chave)["checkin"] is None
    assert session.query(CheckinTreino).count() == len(CHECKINS) + (1 if esperado is True else 0)


# --- os 21 corpos de validacao do oraculo (ADR 0012, itens 1, 2 e 7) ----------------------------------------------------------


def _motivo_bate(motivo: str, detalhe: list[dict]) -> bool:
    """O 422 aponta o campo que o oraculo diz: `loc` ou `type` (campo ausente), nunca o valor."""
    locs = [list(e["loc"]) for e in detalhe]
    if motivo == "obrigatorio":
        return any(e["type"] == "missing" for e in detalhe)
    if motivo == "observacao":
        return any(e["type"] == "value_error" and loc == ["body"] for e, loc in zip(detalhe, locs))
    if motivo == "atalho":
        return any("atalhos" in loc for loc in locs) or any(e["msg"].endswith("atalhos repetidos") for e in detalhe)
    return any(motivo in loc for loc in locs)


@pytest.mark.parametrize("descricao,corpo,valido,motivo", O.VALIDACAO, ids=[v[0] for v in O.VALIDACAO])
def test_validacao_do_put_igual_ao_oraculo(client, banco, session, descricao, corpo, valido, motivo):
    atleta, _, ids = banco
    r = client.put(f"/atletas/{atleta}/atividades/{ids['2026-11-05/cor1']}/checkin", json=corpo)  # dentro do prazo, sem check-in
    if valido:
        assert r.status_code == 200, r.text
        j = r.json()
        assert (j["pse"], j["sensacao"], j["nada_a_relatar"]) == (corpo["pse"], corpo["sensacao"], corpo["nada_a_relatar"])
        assert [a["chave"] for a in j["atalhos"]] == sorted(corpo["atalhos"], key=list(O.VALIDACAO[6][1]["atalhos"]).index)
        assert j["texto"] == corpo["texto"]
        assert session.query(CheckinTreino).count() == len(CHECKINS) + 1
    else:
        assert r.status_code == 422, r.text
        detalhe = r.json()["detail"]
        assert all(set(e) == {"loc", "msg", "type"} for e in detalhe) and "input" not in r.text and "ctx" not in r.text
        assert _motivo_bate(motivo, detalhe), detalhe
        assert session.query(CheckinTreino).count() == len(CHECKINS)


def test_oraculo_de_validacao_tem_21_casos():
    assert len(O.VALIDACAO) == 21 and len(O.CARGA_PSE_ESPERADA) == 18


# --- nenhum valor do check-in em log nem em 422 (ADR 0012, item 5) ----------------------------------------------------------

MARCADOR = "MARCADOR-SINTETICO-123"


def test_get_da_atividade_e_pendentes_nao_levam_o_checkin_ao_log(client, banco, session, caplog):
    atleta, _, ids = banco
    c = session.query(CheckinTreino).filter_by(atividade_id=ids["2026-11-09/cor2"]).one()
    c.texto = MARCADOR
    session.commit()
    caplog.set_level(logging.DEBUG)
    j = _get(client, banco, "2026-11-09/cor2")
    assert j["checkin"]["texto"] == MARCADOR  # sai para o proprio atleta...
    assert MARCADOR not in json.dumps(j["carga_pse"])  # ...mas nao na carga
    r = client.get(f"/atletas/{atleta}/checkins/pendentes")
    assert r.status_code == 200 and MARCADOR not in r.text
    r = client.get(f"/atletas/{atleta}/checkins/pendentes", params={"dias": MARCADOR})
    assert r.status_code == 422 and MARCADOR not in r.text and "input" not in r.text and "ctx" not in r.text
    assert MARCADOR not in caplog.text
