"""Textos da carga e `forma_do_dia` no GET da atividade (issue #464, spec #463, ADR 0004 adendo 12), contra o oraculo da carga (#137).

Valores esperados escritos a mao a partir de docs/metricas/carga-oraculo.md (SERIE e ESPERADO), arredondados a 1 casa.
"""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import criar_app
from tests.acesso_de_teste import sem_login
from app.metricas.serie_carga import MOTIVOS
from app.servicos import carga_textos as ct
from fastapi.testclient import TestClient
from sqlalchemy import select

_spec = importlib.util.spec_from_file_location("_test_carga_rotas", Path(__file__).with_name("test_carga.py"))
_t = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _t
_spec.loader.exec_module(_t)
_atleta = _t._atleta

M = "−"


@pytest.fixture
def client(session):
    app = sem_login(criar_app("http://localhost:8081"))
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def _get(session, client, atleta_id, fonte):
    ids = {int(f): i for f, i in session.execute(select(Atividade.fonte_id, Atividade.id))}
    return client.get(f"/atletas/{atleta_id}/atividades/{ids[fonte]}").json()


def test_carga_calculada_traz_textos_prontos(session, client):
    atleta_id = _atleta(session)
    j = _get(session, client, atleta_id, 4000000022)["carga"]  # 21,919391 pelo pace
    assert (j["estado"], j["valor_texto"], j["metodo_texto"], j["texto"]) == ("calculada", "21,9", "Estimada pelo pace.", None)
    j = _get(session, client, atleta_id, 4000000019)["carga"]  # 54,668975 pela FC
    assert (j["valor_texto"], j["metodo_texto"]) == ("54,7", "Estimada pela FC.")


def test_carga_sem_carga_traz_o_texto_do_motivo(session, client):
    atleta_id = _atleta(session)
    j = _get(session, client, atleta_id, 4000000004)["carga"]
    assert j["motivo"] == "modalidade_sem_carga" and j["texto"] == "Este tipo de treino não tem carga estimada."
    assert j["valor_texto"] is None and j["metodo_texto"] is None
    j = _get(session, client, atleta_id, 4000000001)["carga"]
    assert j["motivo"] == "sem_limiar_na_data" and j["texto"] == "Sem o limiar cadastrado para esta data, não dá para estimar a carga."


def test_todo_motivo_da_carga_tem_texto():
    assert set(ct.MOTIVO_TEXTO) == set(MOTIVOS)


def test_forma_calculada_depois_dos_42_dias(session, client):
    f = _get(session, client, _atleta(session), 4000000022)["forma_do_dia"]  # 16/04: ctl 6,007 atl 5,820 tsb 0,187
    assert f == {"estado": "calculada", "data_local": "2025-04-16", "ctl_texto": "6,0", "atl_texto": "5,8", "tsb_texto": "+0,2",
                 "texto_aprendendo": None, "sem_carga_no_dia": 0, "texto_sem_carga": None}


def test_forma_aprendendo_esconde_os_tres_numeros(session, client):
    atleta_id = _atleta(session)
    f = _get(session, client, atleta_id, 4000000021)["forma_do_dia"]  # 15/04, dia 41 da serie: falta 1 dia
    assert f["estado"] == "aprendendo" and f["texto_aprendendo"] == "Ainda aprendendo a sua forma: falta 1 dia de histórico para estimar."
    assert f["ctl_texto"] is f["atl_texto"] is f["tsb_texto"] is None
    f = _get(session, client, atleta_id, 4000000006)["forma_do_dia"]  # 08/03, dia 3
    assert f["texto_aprendendo"] == "Ainda aprendendo a sua forma: faltam 39 dias de histórico para estimar."


def test_forma_conta_treino_sem_carga_no_dia(session, client):
    f = _get(session, client, _atleta(session), 4000000006)["forma_do_dia"]  # 08/03: 2 atividades, 1 sem carga
    assert f["sem_carga_no_dia"] == 1
    assert f["texto_sem_carga"] == "Há 1 treino deste dia sem carga calculada; a forma pode estar subestimada."


def test_forma_do_dia_sem_serie_quando_nada_foi_calculado(session, client):
    atleta_id = _atleta(session, calcular=False)
    j = _get(session, client, atleta_id, 4000000022)
    assert j["carga"]["estado"] == "pendente"
    assert j["forma_do_dia"] == {"estado": "sem_serie", "data_local": "2025-04-16", "ctl_texto": None, "atl_texto": None,
                                 "tsb_texto": None, "texto_aprendendo": None, "sem_carga_no_dia": 0, "texto_sem_carga": None}


def test_forma_do_dia_sem_serie_sem_saude(session, client):
    atleta_id = _atleta(session, "exportacao_carga_sem_saude.zip")
    j = _get(session, client, atleta_id, 4000000022)
    assert j["carga"]["estado"] == "sem_carga" and j["forma_do_dia"]["estado"] == "sem_serie"


def test_multiesporte_pai_e_troca_sem_carga_sem_forma_e_nao_editaveis(session, client):
    atleta_id = _atleta(session)
    ign = session.scalars(select(Atividade).where(Atividade.subtipo.in_(["multiesporte_pai", "troca"]))).all()
    assert ign
    for a in ign:
        j = client.get(f"/atletas/{atleta_id}/atividades/{a.id}").json()
        assert j["carga"] is None and j["forma_do_dia"] is None and j["transicao"]["editavel"] is False


def test_formatacao():
    assert ct.tsb_texto(-11.64) == f"{M}11,6" and ct.tsb_texto(3.16) == "+3,2"
    assert ct.tsb_texto(0.0) == "0,0" and ct.tsb_texto(-0.04) == "0,0" and ct.tsb_texto(0.04) == "0,0"
    assert ct.numero_texto(87.44) == "87,4" and ct.numero_texto(0.0) == "0,0"
    assert ct.sem_carga_texto(0) is None and "2 treinos deste dia" in ct.sem_carga_texto(2)


def test_editavel_pela_modalidade_e_409_quando_nao(session, client):
    a = Atleta(nome="Ana")
    session.add(a)
    session.commit()
    for i, (mod, esperado) in enumerate([("corrida", True), ("natacao", True), ("ciclismo", True), ("outra", False)]):
        at = Atividade(atleta_id=a.id, fonte="teste", fonte_id=str(i), modalidade=mod, duracao_s=1800.0,
                       inicio=datetime(2025, 3, 5 + i, 9, tzinfo=timezone.utc))
        session.add(at)
        session.commit()
        url = f"/atletas/{a.id}/atividades/{at.id}"
        assert client.get(url).json()["transicao"] == {"valor": False, "origem": None, "editavel": esperado}
        p = client.put(url + "/transicao", json={"transicao": True})
        d = client.delete(url + "/transicao")
        if esperado:
            assert p.json()["editavel"] is True and p.json()["origem"] == "atleta" and d.json()["editavel"] is True
        else:
            assert (p.status_code, d.status_code) == (409, 409)
            assert p.json() == {"detail": "Este treino não tem rótulo de transição."}
            assert client.get(url).json()["transicao"] == {"valor": False, "origem": None, "editavel": False}  # nada gravado


def test_pai_e_troca_do_multiesporte_tambem_dao_409(session, client):
    atleta_id = _atleta(session)
    ign = session.scalars(select(Atividade).where(Atividade.subtipo.in_(["multiesporte_pai", "troca"]))).all()
    assert ign
    for at in ign:
        r = client.put(f"/atletas/{atleta_id}/atividades/{at.id}/transicao", json={"transicao": True})
        assert r.status_code == 409
        assert client.delete(f"/atletas/{atleta_id}/atividades/{at.id}/transicao").status_code == 409
