"""Contas, entrar, sair, trocar a senha e forca bruta (issue #499, ADR 0016). Tudo sintetico; senhas de teste so aqui."""

from datetime import datetime, timedelta, timezone

import pytest
from app.autenticacao import conta_liberada
from app.db.models import Atleta, Conta, Professor, Assessoria, Sessao, TentativaLogin
from app.db.session import get_session
from app.main import criar_app
from app.servicos import conta as svc
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

SENHA = "senha-de-teste-123"
EMAIL = "ana@exemplo.com"
T0 = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def app(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    return a


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def pessoas(session):
    ass = Assessoria(nome="Assessoria Teste")
    session.add(ass)
    session.flush()
    ana = Atleta(nome="Ana Teste", assessoria_id=ass.id)
    prof = Professor(nome="Paulo Teste", assessoria_id=ass.id)
    session.add_all([ana, prof])
    session.flush()
    svc.criar_conta(session, EMAIL, SENHA, atleta_id=ana.id)
    svc.criar_conta(session, "paulo@exemplo.com", SENHA, professor_id=prof.id)
    session.commit()
    return ana, prof


def _entrar(client, email=EMAIL, senha=SENHA):
    return client.post("/sessao", json={"email": email, "senha": senha})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_entrar_devolve_o_acesso_e_quem_sou(client, pessoas):
    ana, _ = pessoas
    r = _entrar(client, " ANA@Exemplo.com ")  # e-mail sem diferenca de caixa e espaco
    assert r.status_code == 200
    j = r.json()
    assert j["papel"] == "atleta" and j["atleta_id"] == ana.id and j["professor_id"] is None and j["nome"] == "Ana Teste"
    assert j["troca_de_senha_obrigatoria"] is False and len(j["token"]) >= 40
    eu = client.get("/sessao", headers=_auth(j["token"])).json()
    assert eu["atleta_id"] == ana.id and eu["papel"] == "atleta" and "token" not in eu
    r = _entrar(client, "paulo@exemplo.com")
    assert r.json()["papel"] == "professor" and r.json()["atleta_id"] is None


def test_o_token_nao_e_guardado_so_o_hash(client, session, pessoas):
    token = _entrar(client).json()["token"]
    s = session.scalars(select(Sessao)).one()
    assert s.token_hash == svc.hash_do_token(token) and token not in (s.token_hash,)
    assert (svc_utc(s.expira_em) - svc_utc(s.criada_em)) == timedelta(days=30)


def svc_utc(d):
    from app.ingestao.garmin.unidades import para_utc

    return para_utc(d)


def test_senha_nunca_em_claro_no_banco(session, pessoas):
    c = session.scalars(select(Conta).where(Conta.email == EMAIL)).one()
    assert SENHA not in c.senha_hash and c.senha_hash.startswith("$argon2id$")


@pytest.mark.parametrize("email,senha", [(EMAIL, "senha-errada-000"), ("ninguem@exemplo.com", SENHA)])
def test_credencial_errada_e_email_inexistente_dao_o_mesmo_401(client, pessoas, email, senha):
    r = _entrar(client, email, senha)
    assert r.status_code == 401 and r.json() == {"detail": "e-mail ou senha incorretos"}
    assert r.headers["www-authenticate"] == "Bearer"


def test_conta_desativada_da_o_mesmo_401(client, session, pessoas):
    svc.desativar(session, svc.conta_por_email(session, EMAIL))
    session.commit()
    r = _entrar(client)
    assert r.status_code == 401 and r.json() == {"detail": "e-mail ou senha incorretos"}


def test_desativar_revoga_as_sessoes(client, session, pessoas):
    token = _entrar(client).json()["token"]
    svc.desativar(session, svc.conta_por_email(session, EMAIL))
    session.commit()
    assert client.get("/sessao", headers=_auth(token)).status_code == 401


@pytest.mark.parametrize("cab", [{}, {"Authorization": "Bearer"}, {"Authorization": "Bearer nao-existe"}, {"Authorization": "Basic abc"}])
def test_sem_acesso_valido_e_401(client, pessoas, cab):
    r = client.get("/sessao", headers=cab)
    assert r.status_code == 401 and r.json() == {"detail": "não autenticado"}


def test_sair_revoga_so_a_sessao_atual(client, pessoas):
    a = _entrar(client).json()["token"]
    b = _entrar(client).json()["token"]
    assert client.delete("/sessao", headers=_auth(a)).status_code == 204
    assert client.get("/sessao", headers=_auth(a)).status_code == 401
    assert client.get("/sessao", headers=_auth(b)).status_code == 200


def test_sessao_expirada_e_401(client, session, pessoas):
    token = _entrar(client).json()["token"]
    s = session.scalars(select(Sessao)).one()
    s.expira_em = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.commit()
    assert client.get("/sessao", headers=_auth(token)).status_code == 401


def test_trocar_senha_revoga_todas_e_devolve_acesso_novo(client, pessoas):
    a = _entrar(client).json()["token"]
    b = _entrar(client).json()["token"]
    r = client.put("/conta/senha", headers=_auth(a), json={"senha_atual": SENHA, "senha_nova": "outra-senha-forte-9"})
    assert r.status_code == 200
    novo = r.json()["token"]
    assert client.get("/sessao", headers=_auth(a)).status_code == 401 and client.get("/sessao", headers=_auth(b)).status_code == 401
    assert client.get("/sessao", headers=_auth(novo)).status_code == 200
    assert _entrar(client).status_code == 401 and _entrar(client, senha="outra-senha-forte-9").status_code == 200


@pytest.mark.parametrize("atual,nova,tipo", [
    ("errada-errada-1", "outra-senha-forte-9", "senha_atual_incorreta"),
    (SENHA, "x1y2z3", "senha_nova_invalida"),
    (SENHA, "1234567890", "senha_nova_invalida"),  # comum
    (SENHA, EMAIL, "senha_nova_invalida"),
    (SENHA, SENHA, "senha_nova_invalida"),  # igual a atual
])
def test_trocar_senha_recusa_e_nao_repete_a_senha(client, pessoas, atual, nova, tipo):
    token = _entrar(client).json()["token"]
    r = client.put("/conta/senha", headers=_auth(token), json={"senha_atual": atual, "senha_nova": nova})
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == tipo
    assert atual not in r.text and nova not in r.text
    assert client.get("/sessao", headers=_auth(token)).status_code == 200  # nada mudou


def test_422_nao_repete_a_entrada(client, pessoas):
    r = client.post("/sessao", json={"email": EMAIL, "senha": ""})
    assert r.status_code == 422 and "input" not in r.text and "ctx" not in r.text


def test_forca_bruta_5_falhas_travam_ate_com_a_senha_certa(client, pessoas):
    for _ in range(5):
        assert _entrar(client, senha="errada-errada-1").status_code == 401
    r = _entrar(client)  # senha certa, mas travado
    assert r.status_code == 429 and 1 <= r.json()["espere_s"] <= 900 and r.headers["retry-after"] == str(r.json()["espere_s"])
    assert _entrar(client, "outra@exemplo.com").status_code == 401  # outro e-mail nao e afetado


def test_forca_bruta_libera_depois_da_janela_e_sucesso_zera(session, pessoas):
    for i in range(5):
        with pytest.raises(svc.CredencialInvalida):
            svc.entrar(session, EMAIL, "errada-errada-1", T0 + timedelta(minutes=i))
    with pytest.raises(svc.ForcaBruta) as e:
        svc.entrar(session, EMAIL, SENHA, T0 + timedelta(minutes=5))
    assert e.value.espere_s == 10 * 60  # a mais antiga sai da janela 15 min depois de T0
    conta, _ = svc.entrar(session, EMAIL, SENHA, T0 + timedelta(minutes=15, seconds=1))
    assert conta.email == EMAIL
    assert session.scalars(select(TentativaLogin)).all() == []  # sucesso zera a conta de falhas


def test_tentativa_guarda_so_o_hash_do_email(client, session, pessoas):
    _entrar(client, "Quem@Exemplo.com", "errada-errada-1")
    t = session.scalars(select(TentativaLogin)).one()
    assert t.email_hash == svc.hash_do_email("quem@exemplo.com") and "exemplo" not in t.email_hash


def test_troca_obrigatoria_bloqueia_as_rotas_liberadas(app, session, pessoas):
    ana, _ = pessoas
    c = svc.conta_por_email(session, EMAIL)
    senha_temp = svc.redefinir_senha(session, c)
    session.commit()

    @app.get("/_teste_liberada")
    def _rota(conta=Depends(conta_liberada)):
        return {"ok": True}

    cl = TestClient(app)
    r = _entrar(cl, senha=senha_temp)
    assert r.status_code == 200 and r.json()["troca_de_senha_obrigatoria"] is True
    h = _auth(r.json()["token"])
    r2 = cl.get("/_teste_liberada", headers=h)
    assert r2.status_code == 403 and r2.json()["detail"][0]["type"] == "troca_de_senha_obrigatoria"
    assert cl.get("/sessao", headers=h).status_code == 200  # as rotas da propria troca seguem abertas
    novo = cl.put("/conta/senha", headers=h, json={"senha_atual": senha_temp, "senha_nova": "senha-nova-forte-7"}).json()["token"]
    assert cl.get("/_teste_liberada", headers=_auth(novo)).status_code == 200


def test_redefinir_revoga_sessoes_e_a_senha_antiga_para_de_valer(client, session, pessoas):
    token = _entrar(client).json()["token"]
    nova = svc.redefinir_senha(session, svc.conta_por_email(session, EMAIL))
    session.commit()
    assert client.get("/sessao", headers=_auth(token)).status_code == 401
    assert _entrar(client).status_code == 401 and _entrar(client, senha=nova).status_code == 200


def test_criar_conta_regras(session, pessoas):
    ana, prof = pessoas
    with pytest.raises(svc.ContaInvalida):
        svc.criar_conta(session, "outra@exemplo.com", SENHA, atleta_id=ana.id)  # atleta ja tem conta
    with pytest.raises(svc.ContaInvalida):
        svc.criar_conta(session, EMAIL.upper(), SENHA, professor_id=None, atleta_id=999)  # e-mail repetido / atleta inexistente
    with pytest.raises(svc.ContaInvalida):
        svc.criar_conta(session, "x@exemplo.com", SENHA)  # sem papel
    with pytest.raises(svc.ContaInvalida):
        svc.criar_conta(session, "x@exemplo.com", SENHA, atleta_id=ana.id, professor_id=prof.id)  # dois papeis
    with pytest.raises(svc.SenhaInvalida):
        svc.criar_conta(session, "y@exemplo.com", "curta", professor_id=prof.id)


def test_nada_sensivel_no_log(client, pessoas, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    _entrar(client, "marca-email@exemplo.com", "MarcaSenha-Secreta-1")
    token = _entrar(client).json()["token"]
    client.put("/conta/senha", headers=_auth(token), json={"senha_atual": "MarcaSenha-Secreta-1", "senha_nova": "MarcaNova-Secreta-2"})
    texto = caplog.text
    for marca in ("marca-email", "MarcaSenha", "MarcaNova", token, SENHA):
        assert marca not in texto


def test_limpar_expiradas(session, pessoas):
    c = svc.conta_por_email(session, EMAIL)
    session.add_all([
        Sessao(conta_id=c.id, token_hash="a", criada_em=T0, expira_em=T0 + timedelta(days=30)),
        Sessao(conta_id=c.id, token_hash="b", criada_em=T0 - timedelta(days=40), expira_em=T0 - timedelta(days=10)),
        Sessao(conta_id=c.id, token_hash="c", criada_em=T0, expira_em=T0 + timedelta(days=30), revogada_em=T0),
        TentativaLogin(email_hash="x", ocorrida_em=T0 - timedelta(days=31), ok=False),
        TentativaLogin(email_hash="y", ocorrida_em=T0 - timedelta(days=2), ok=False),
    ])
    session.commit()
    assert svc.limpar_expiradas(session, T0) == (2, 1)
