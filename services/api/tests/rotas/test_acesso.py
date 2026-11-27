"""Controle de acesso em todas as rotas (issue #500, ADR 0016, item 5). Pessoas e e-mails FICTICIOS; sessao de verdade, sem o helper `sem_login`.

Ordem das respostas: 401 (sem sessao) -> 403 (troca de senha pendente) -> 404 (de outro ou inexistente) -> 422/409 (da rota).
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.autenticacao import atleta_da_sessao, professor_da_sessao
from app.servicos.consentimento import TERMO_VIGENTE
from app.db.models import Assessoria, Atividade, Atleta, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.main import criar_app
from app.servicos import conta as svc
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

SENHA = "senha-de-teste-123"
AGORA = datetime.now(timezone.utc)
# unicas rotas sem sessao (ADR 0016, item 4)
PUBLICAS = {("get", "/health"), ("post", "/sessao")}


@pytest.fixture
def app(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
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
    ativ = Atividade(atleta_id=ana.id, fonte="t", fonte_id="1", modalidade="corrida", inicio=AGORA - timedelta(days=1), duracao_s=1800,
                     tipo_treino="leve", tipo_origem="semana_padrao", tipo_versao="tipo_treino@1", tipo_divergencia="sem_esforco")
    session.add(ativ)
    session.add(VinculoProfessorAtleta(professor_id=paulo.id, atleta_id=ana.id, consentimento_em=AGORA - timedelta(days=5), termo_versao=TERMO_VIGENTE))
    session.add(VinculoProfessorAtleta(professor_id=lia.id, atleta_id=ana.id, consentimento_em=None, termo_versao=TERMO_VIGENTE))  # vinculo sem consentimento
    for email, kw in (("ana@exemplo.com", dict(atleta_id=ana.id)), ("bia@exemplo.com", dict(atleta_id=bia.id)),
                      ("paulo@exemplo.com", dict(professor_id=paulo.id)), ("lia@exemplo.com", dict(professor_id=lia.id))):
        svc.criar_conta(session, email, SENHA, **kw)
    session.commit()
    return dict(ana=ana.id, bia=bia.id, paulo=paulo.id, lia=lia.id, ativ=ativ.id)


def _token(client, quem):
    r = client.post("/sessao", json={"email": f"{quem}@exemplo.com", "senha": SENHA})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _rotas(app):
    """(metodo, caminho) de cada operacao do OpenAPI do app real."""
    return sorted((m, p) for p, ops in app.openapi()["paths"].items() for m in ops if (m, p) not in PUBLICAS)


def _url(caminho, **ids):
    return caminho.format(**{"atleta_id": 1, "professor_id": 1, "atividade_id": 1, "serie_id": "corrida.pace.leve", **ids})


# ---------- o teste que percorre as rotas: rota nova sem protecao quebra aqui ----------

def test_toda_rota_do_openapi_exige_sessao(app):
    sem_seguranca = [f"{m.upper()} {p}" for m, p in _rotas(app)
                     if "security" not in app.openapi()["paths"][p][m]]
    assert sem_seguranca == []


def test_toda_rota_de_atleta_ou_de_professor_confere_o_id_com_a_sessao(app):
    def deps(d):
        yield d.call
        for s in d.dependencies:
            yield from deps(s)

    for r in app.routes:
        if not isinstance(r, APIRoute) or r.path in {p for _, p in PUBLICAS}:
            continue
        chamadas = set(deps(r.dependant)) | {d.dependency for d in r.dependencies}
        if r.path.startswith("/atletas/"):
            assert atleta_da_sessao in chamadas, r.path
        elif r.path.startswith("/professores/"):
            assert professor_da_sessao in chamadas or any(c.__name__ == "professor_da_rota" for c in chamadas), r.path
        else:
            assert r.path in {"/sessao", "/conta/senha", "/termo-de-consentimento"}, f"rota fora do mapa de acesso: {r.path}"


def test_a_lista_de_rotas_publicas_e_so_a_do_adr(app):
    publicas = {(m, p) for p, ops in app.openapi()["paths"].items() for m in ops if "security" not in ops[m]}
    assert publicas == PUBLICAS


# ---------- 401 ----------

def test_sem_sessao_toda_rota_responde_401(app, client, mundo):
    for m, p in _rotas(app):
        r = client.request(m.upper(), _url(p, atleta_id=mundo["ana"], professor_id=mundo["paulo"], atividade_id=mundo["ativ"]))
        assert r.status_code == 401, f"{m} {p}"
        assert r.headers["www-authenticate"] == "Bearer"


def test_o_401_e_o_mesmo_para_ausente_errado_e_revogado(client, mundo):
    url = f"/atletas/{mundo['ana']}/carga"
    h = _token(client, "ana")
    assert client.get(url, headers=h).status_code == 200
    assert client.delete("/sessao", headers=h).status_code == 204
    revogado = client.get(url, headers=h)
    ausente = client.get(url)
    errado = client.get(url, headers={"Authorization": "Bearer nao-e-um-token"})
    outro_esquema = client.get(url, headers={"Authorization": "Basic YWJjOmRlZg=="})
    for r in (revogado, errado, outro_esquema):
        assert r.status_code == 401 and r.json() == ausente.json()


def test_o_401_vem_antes_do_404_e_antes_do_422(client, mundo):
    assert client.put(f"/atletas/{mundo['bia']}/atividades/{mundo['ativ']}/transicao", json={"lixo": 1}).status_code == 401
    assert client.put(f"/professores/{mundo['lia']}/tipos-de-treino", json=[]).status_code == 401


# ---------- 404: recurso de outro ----------

def test_atleta_de_outro_recebe_o_mesmo_404_de_atleta_inexistente_em_toda_rota(app, client, mundo):
    h = _token(client, "bia")
    for m, p in _rotas(app):
        if not p.startswith("/atletas/"):
            continue
        alheio = client.request(m.upper(), _url(p, atleta_id=mundo["ana"], atividade_id=mundo["ativ"]), headers=h)
        nao_existe = client.request(m.upper(), _url(p, atleta_id=999999, atividade_id=mundo["ativ"]), headers=h)
        assert alheio.status_code == 404, f"{m} {p}"
        assert alheio.status_code == nao_existe.status_code and alheio.content == nao_existe.content, f"{m} {p}"


def test_professor_nao_usa_as_rotas_de_atleta(app, client, mundo):
    """Mesmo com vinculo e consentimento: o que o professor ve do aluno chega pela caixa do dia (ADR 0016, item 5)."""
    h = _token(client, "paulo")
    for m, p in _rotas(app):
        if p.startswith("/atletas/"):
            r = client.request(m.upper(), _url(p, atleta_id=mundo["ana"], atividade_id=mundo["ativ"]), headers=h)
            assert r.status_code == 404, f"{m} {p}"


def test_atleta_nao_usa_as_rotas_de_professor(client, mundo):
    h = _token(client, "ana")
    assert client.get(f"/professores/{mundo['paulo']}/caixa-do-dia", headers=h).status_code == 404
    assert client.put(f"/professores/{mundo['paulo']}/tipos-de-treino", json=[], headers=h).status_code == 404


def test_professor_de_outro_recebe_o_404_uniforme_igual_ao_inexistente(client, mundo):
    h = _token(client, "lia")
    for caminho, metodo in (("caixa-do-dia", "get"), ("tipos-de-treino", "put")):
        outro = client.request(metodo.upper(), f"/professores/{mundo['paulo']}/{caminho}", headers=h, json=[] if metodo == "put" else None)
        nenhum = client.request(metodo.upper(), f"/professores/999999/{caminho}", headers=h, json=[] if metodo == "put" else None)
        assert outro.status_code == nenhum.status_code == 404 and outro.content == nenhum.content


def test_o_404_vem_antes_do_422_do_corpo(client, mundo):
    h = _token(client, "bia")
    r = client.put(f"/atletas/{mundo['ana']}/semana-padrao", json={"lixo": 1}, headers=h)
    assert r.status_code == 404
    r = client.put(f"/professores/{mundo['paulo']}/tipos-de-treino", json=[{"atividade_id": 1, "tipo_treino": "nao_existe"}],
                   headers=_token(client, "lia"))
    assert r.status_code == 404


# ---------- o dono passa ----------

def test_o_atleta_dono_le_os_proprios_dados(client, mundo):
    h = _token(client, "ana")
    a = mundo["ana"]
    for url in (f"/atletas/{a}/carga", f"/atletas/{a}/semana-padrao", f"/atletas/{a}/checkins/pendentes", f"/atletas/{a}/treinos-de-transicao",
                f"/atletas/{a}/atividades/{mundo['ativ']}"):
        assert client.get(url, headers=h).status_code == 200, url


def test_o_professor_dono_le_a_propria_caixa(client, mundo):
    r = client.get(f"/professores/{mundo['paulo']}/caixa-do-dia", headers=_token(client, "paulo"))
    assert r.status_code == 200


# ---------- transicao so pelo atleta dono ----------

def test_correcao_da_transicao_so_pelo_atleta_dono(client, mundo):
    url = f"/atletas/{mundo['ana']}/atividades/{mundo['ativ']}/transicao"
    corpo = {"transicao": True}
    for quem in ("paulo", "lia", "bia"):
        h = _token(client, quem)
        assert client.put(url, json=corpo, headers=h).status_code == 404, quem
        assert client.delete(url, headers=h).status_code == 404, quem
    # o dono passa pela conferencia de acesso (o que a rota responde depois e problema dela, nunca 401 nem 404 de atleta)
    r = client.delete(url, headers=_token(client, "ana"))
    assert r.status_code not in (401, 403) and r.json().get("detail") != "atleta não encontrado"


# ---------- professor sem consentimento ----------

def test_professor_sem_consentimento_nao_confirma_o_tipo_de_treino_do_aluno(client, mundo):
    corpo = [{"atividade_id": mundo["ativ"], "tipo_treino": "leve"}]
    sem = client.put(f"/professores/{mundo['lia']}/tipos-de-treino", json=corpo, headers=_token(client, "lia"))
    inexistente = client.put(f"/professores/{mundo['lia']}/tipos-de-treino", json=[{"atividade_id": 999999, "tipo_treino": "leve"}],
                             headers=_token(client, "lia"))
    assert sem.status_code == 404 and sem.content == inexistente.content


def test_a_caixa_do_professor_sem_consentimento_nao_traz_o_aluno(client, mundo):
    j = client.get(f"/professores/{mundo['lia']}/caixa-do-dia", headers=_token(client, "lia")).json()
    assert j["alunos"] == [] and j["novos"] == []


# ---------- troca de senha pendente e conta desativada ----------

def test_com_a_troca_de_senha_pendente_a_rota_de_dado_da_403_e_o_resto_funciona(client, session, mundo):
    from app.db.models import Conta
    from sqlalchemy import select

    c = session.scalars(select(Conta).where(Conta.email == "ana@exemplo.com")).one()
    svc.redefinir_senha(session, c)  # senha provisoria; a conta fica com troca obrigatoria
    c.senha_hash = svc._gerar_hash(SENHA)  # (o teste conhece a senha)
    session.commit()
    h = _token(client, "ana")
    r = client.get(f"/atletas/{mundo['ana']}/carga", headers=h)
    assert r.status_code == 403 and r.json()["detail"][0]["type"] == "troca_de_senha_obrigatoria"
    assert client.get("/sessao", headers=h).json()["troca_de_senha_obrigatoria"] is True
    novo = client.put("/conta/senha", json={"senha_atual": SENHA, "senha_nova": "outra-senha-de-teste-9"}, headers=h)
    assert novo.status_code == 200
    h2 = {"Authorization": f"Bearer {novo.json()['token']}"}
    assert client.get(f"/atletas/{mundo['ana']}/carga", headers=h2).status_code == 200
    assert client.get(f"/atletas/{mundo['ana']}/carga", headers=h).status_code == 401  # a sessao antiga morreu com a troca


def test_conta_desativada_perde_o_acesso_na_hora(client, session, mundo):
    from app.db.models import Conta
    from sqlalchemy import select

    h = _token(client, "bia")
    c = session.scalars(select(Conta).where(Conta.email == "bia@exemplo.com")).one()
    svc.desativar(session, c)
    session.commit()
    assert client.get(f"/atletas/{mundo['bia']}/carga", headers=h).status_code == 401
