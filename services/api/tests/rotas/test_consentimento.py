"""Consentimento registrado pelo atleta (issue #501, ADR 0016, item 7). Sessao de verdade; pessoas e e-mails FICTICIOS."""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Assessoria, Atividade, Atleta, ConsentimentoEvento, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.main import criar_app
from app.servicos import conta as svc_conta
from app.servicos.consentimento import TERMO_TEXTO, TERMO_VIGENTE
from app.servicos.professor import agora_utc
from fastapi.testclient import TestClient
from sqlalchemy import select

SENHA = "senha-de-teste-123"
AGORA = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
OBS = "obs-sintetica-do-treino"


@pytest.fixture
def app(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    a.dependency_overrides[agora_utc] = lambda: AGORA
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mundo(session):
    ass = Assessoria(nome="Assessoria Teste")
    session.add(ass)
    session.flush()
    ana, bia = (Atleta(nome=n, assessoria_id=ass.id) for n in ("Ana Teste", "Bia Teste"))
    paulo, lia = (Professor(nome=n, assessoria_id=ass.id) for n in ("Paulo Teste", "Lia Teste"))
    session.add_all([ana, bia, paulo, lia])
    session.flush()
    for a in (ana, bia):
        session.add(Atividade(atleta_id=a.id, fonte="t", fonte_id=str(a.id), modalidade="corrida", inicio=AGORA - timedelta(days=1),
                              duracao_s=1800, tipo_treino="leve", tipo_origem="semana_padrao", tipo_versao="tipo_treino@1",
                              tipo_divergencia="sem_esforco"))
    # vinculos criados pelo operador, SEM consentimento
    session.add_all([VinculoProfessorAtleta(professor_id=paulo.id, atleta_id=ana.id),
                     VinculoProfessorAtleta(professor_id=paulo.id, atleta_id=bia.id)])
    for email, kw in (("ana@exemplo.com", dict(atleta_id=ana.id)), ("bia@exemplo.com", dict(atleta_id=bia.id)),
                      ("paulo@exemplo.com", dict(professor_id=paulo.id)), ("lia@exemplo.com", dict(professor_id=lia.id))):
        svc_conta.criar_conta(session, email, SENHA, **kw)
    session.commit()
    return dict(ana=ana.id, bia=bia.id, paulo=paulo.id, lia=lia.id)


def _h(client, quem):
    r = client.post("/sessao", json={"email": f"{quem}@exemplo.com", "senha": SENHA})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _aceitar(client, mundo, quem="ana", prof="paulo", versao=TERMO_VIGENTE):
    return client.put(f"/atletas/{mundo[quem]}/professores/{mundo[prof]}/consentimento", json={"termo_versao": versao}, headers=_h(client, quem))


def _alunos(client, mundo):
    j = client.get(f"/professores/{mundo['paulo']}/caixa-do-dia", headers=_h(client, "paulo")).json()
    return sorted(a["atleta_id"] for a in j["alunos"]) + sorted(n["atleta_id"] for n in j["novos"])


# ---------- o termo ----------

def test_o_termo_vem_marcado_como_provisorio_e_so_com_sessao(client, mundo):
    assert client.get("/termo-de-consentimento").status_code == 401
    for quem in ("ana", "paulo"):
        r = client.get("/termo-de-consentimento", headers=_h(client, quem))
        assert r.status_code == 200
        assert r.json() == {"versao": TERMO_VIGENTE, "provisorio": True, "texto": TERMO_TEXTO}
    assert TERMO_VIGENTE == "termo@0-provisorio" and "provisório" in TERMO_TEXTO


# ---------- registrar ----------

def test_vinculo_sem_consentimento_aparece_como_aguardando_o_atleta(client, mundo):
    j = client.get(f"/atletas/{mundo['ana']}/professores", headers=_h(client, "ana")).json()
    assert j["termo_vigente"] == TERMO_VIGENTE
    assert [(p["professor_id"], p["nome"], p["consentimento"], p["termo_versao"]) for p in j["professores"]] == [
        (mundo["paulo"], "Paulo Teste", False, None)]


def test_aceitar_grava_data_e_versao_juntas_e_um_evento(client, session, mundo):
    r = _aceitar(client, mundo)
    assert r.status_code == 200
    j = r.json()
    assert j["consentimento"] is True and j["termo_versao"] == TERMO_VIGENTE and j["consentimento_revogado_em"] is None
    v = session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"]))
    assert v.termo_versao == TERMO_VIGENTE and v.consentimento_em is not None
    ev = session.scalars(select(ConsentimentoEvento)).all()
    assert [(e.atleta_id, e.professor_id, e.acao, e.termo_versao) for e in ev] == [(mundo["ana"], mundo["paulo"], "aceito", TERMO_VIGENTE)]
    assert client.get(f"/atletas/{mundo['ana']}/professores", headers=_h(client, "ana")).json()["professores"][0]["consentimento"] is True


def test_aceitar_de_novo_nao_duplica_o_evento(client, session, mundo):
    _aceitar(client, mundo)
    assert _aceitar(client, mundo).status_code == 200
    assert len(session.scalars(select(ConsentimentoEvento)).all()) == 1


def test_versao_diferente_da_vigente_da_409_e_nao_grava(client, session, mundo):
    r = _aceitar(client, mundo, versao="termo@99")
    assert r.status_code == 409
    assert session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"])).consentimento_em is None
    assert session.scalars(select(ConsentimentoEvento)).all() == []


def test_sem_vinculo_criado_pelo_operador_o_atleta_nao_se_vincula(client, mundo):
    r = _aceitar(client, mundo, prof="lia")  # lia nao tem vinculo com a ana
    assert r.status_code == 404


def test_corpo_invalido_da_422_sem_repetir_o_enviado(client, mundo):
    r = client.put(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", json={"termo_versao": ""}, headers=_h(client, "ana"))
    assert r.status_code == 422 and "input" not in r.text


# ---------- quem pode ----------

def test_so_o_atleta_dono_registra_e_retira(client, mundo):
    url = f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento"
    corpo = {"termo_versao": TERMO_VIGENTE}
    assert client.put(url, json=corpo).status_code == 401
    for quem in ("paulo", "bia", "lia"):
        h = _h(client, quem)
        assert client.put(url, json=corpo, headers=h).status_code == 404, quem
        assert client.delete(url, headers=h).status_code == 404, quem
        assert client.get(f"/atletas/{mundo['ana']}/professores", headers=h).status_code == 404, quem


def test_o_professor_nao_aceita_em_nome_do_atleta_e_nada_muda(client, session, mundo):
    client.put(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", json={"termo_versao": TERMO_VIGENTE}, headers=_h(client, "paulo"))
    assert session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"])).consentimento_em is None
    assert _alunos(client, mundo) == []


# ---------- o efeito na caixa do professor ----------

def test_antes_do_aceite_o_professor_nao_ve_o_aluno_e_depois_ve(client, mundo):
    assert _alunos(client, mundo) == []
    _aceitar(client, mundo)
    assert mundo["ana"] in _alunos(client, mundo) and mundo["bia"] not in _alunos(client, mundo)


def test_retirar_tira_o_aluno_da_caixa_na_hora_e_mantem_o_vinculo_e_os_dados(client, session, mundo):
    _aceitar(client, mundo)
    assert mundo["ana"] in _alunos(client, mundo)
    r = client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", headers=_h(client, "ana"))
    assert r.status_code == 204
    assert _alunos(client, mundo) == []  # na mesma leitura seguinte
    corpo = client.get(f"/professores/{mundo['paulo']}/caixa-do-dia", headers=_h(client, "paulo")).text
    assert "Ana Teste" not in corpo
    v = session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"]))
    assert v is not None and v.consentimento_revogado_em is not None  # o vinculo fica
    assert session.scalars(select(Atividade).where(Atividade.atleta_id == mundo["ana"])).first() is not None  # os dados ficam
    assert [e.acao for e in session.scalars(select(ConsentimentoEvento).order_by(ConsentimentoEvento.id))] == ["aceito", "revogado"]
    j = client.get(f"/atletas/{mundo['ana']}/professores", headers=_h(client, "ana")).json()["professores"][0]
    assert j["consentimento"] is False and j["consentimento_revogado_em"] is not None  # volta a "Aguardando voce"


def test_retirar_barra_o_put_em_lote_do_tipo_com_o_mesmo_404_de_inexistente(client, session, mundo):
    _aceitar(client, mundo)
    ativ = session.scalars(select(Atividade).where(Atividade.atleta_id == mundo["ana"])).one().id
    h = _h(client, "paulo")
    url = f"/professores/{mundo['paulo']}/tipos-de-treino"
    assert client.put(url, json=[{"atividade_id": ativ, "tipo_treino": "longo"}], headers=h).status_code == 200
    client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", headers=_h(client, "ana"))
    retirado = client.put(url, json=[{"atividade_id": ativ, "tipo_treino": "leve"}], headers=h)
    inexistente = client.put(url, json=[{"atividade_id": 999999, "tipo_treino": "leve"}], headers=h)
    assert retirado.status_code == 404 and retirado.content == inexistente.content
    session.expire_all()
    assert session.get(Atividade, ativ).tipo_treino == "longo"  # o que o professor confirmou antes continua


def test_retirar_nao_muda_a_caixa_dos_outros_alunos(client, mundo):
    _aceitar(client, mundo, "ana")
    _aceitar(client, mundo, "bia")
    assert {mundo["ana"], mundo["bia"]} <= set(_alunos(client, mundo))
    client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", headers=_h(client, "ana"))
    resto = _alunos(client, mundo)
    assert mundo["bia"] in resto and mundo["ana"] not in resto


def test_aceitar_de_novo_depois_de_retirar_devolve_o_aluno(client, session, mundo):
    _aceitar(client, mundo)
    client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", headers=_h(client, "ana"))
    assert _aceitar(client, mundo).status_code == 200
    assert mundo["ana"] in _alunos(client, mundo)
    v = session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"]))
    assert v.consentimento_revogado_em is None
    assert [e.acao for e in session.scalars(select(ConsentimentoEvento).order_by(ConsentimentoEvento.id))] == ["aceito", "revogado", "aceito"]


def test_retirar_sem_consentimento_ou_duas_vezes_nao_grava_evento(client, session, mundo):
    url = f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento"
    h = _h(client, "ana")
    assert client.delete(url, headers=h).status_code == 204
    _aceitar(client, mundo)
    assert client.delete(url, headers=h).status_code == 204 and client.delete(url, headers=h).status_code == 204
    assert [e.acao for e in session.scalars(select(ConsentimentoEvento))] == ["aceito", "revogado"]


def test_retirar_de_professor_sem_vinculo_da_404(client, mundo):
    assert client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['lia']}/consentimento", headers=_h(client, "ana")).status_code == 404


# ---------- versao do termo ----------

def test_versao_antiga_do_termo_vale_como_sem_consentimento_ate_aceitar_de_novo(client, session, mundo):
    _aceitar(client, mundo)
    assert mundo["ana"] in _alunos(client, mundo)
    session.get(VinculoProfessorAtleta, (mundo["paulo"], mundo["ana"])).termo_versao = "termo@antigo"
    session.commit()
    assert mundo["ana"] not in _alunos(client, mundo)  # o filtro e o unico que decide
    j = client.get(f"/atletas/{mundo['ana']}/professores", headers=_h(client, "ana")).json()["professores"][0]
    assert j["consentimento"] is False and j["termo_desatualizado"] is True
    assert _aceitar(client, mundo).status_code == 200
    assert mundo["ana"] in _alunos(client, mundo)


def test_nada_do_texto_do_atleta_vai_ao_log(client, mundo, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    _aceitar(client, mundo)
    client.delete(f"/atletas/{mundo['ana']}/professores/{mundo['paulo']}/consentimento", headers=_h(client, "ana"))
    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "Ana Teste" not in texto and "ana@exemplo.com" not in texto and SENHA not in texto and OBS not in texto
