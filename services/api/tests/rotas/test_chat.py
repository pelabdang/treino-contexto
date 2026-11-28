"""Rotas do chat (#598, ADR 0017). Sessao de verdade, provedor falso (sem rede), pessoas e numeros sinteticos."""

import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Assessoria, Atividade, Atleta, Conversa, Mensagem, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.llm.camada import ChamadaFerramenta, ErroProvedor, LimiteDoProvedor, ProvedorFalso, Redator, RespostaConversa
from app.main import criar_app
from app.rotas.chat import FRASE_ERRO, PERGUNTAS_POR_HORA, get_redator
from app.servicos import conta as svc
from app.servicos.consentimento import TERMO_VIGENTE
from fastapi.testclient import TestClient

SENHA = "senha-de-teste-123"
MARCA = "MARCA-SINTETICA-PERGUNTA"
AGORA = datetime.now(timezone.utc)


@pytest.fixture
def prov():
    return {"falso": ProvedorFalso(roteiro=[])}


@pytest.fixture
def app(session, prov):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    a.dependency_overrides[get_redator] = lambda: Redator(prov["falso"], "falso", "falso-1")
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
    paulo = Professor(nome="Paulo Teste", assessoria_id=ass.id)
    session.add_all([ana, bia, paulo])
    session.flush()
    inicio = (AGORA - timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
    a1 = Atividade(atleta_id=ana.id, fonte="t", fonte_id="1", modalidade="corrida", inicio=inicio, fuso_min=-180, duracao_s=2820.0,
                   distancia_m=8200.0, fc_media=146.0, tipo_treino="leve")
    session.add(a1)
    session.add(VinculoProfessorAtleta(professor_id=paulo.id, atleta_id=ana.id, consentimento_em=AGORA - timedelta(days=5), termo_versao=TERMO_VIGENTE))
    for email, kw in (("ana@exemplo.com", dict(atleta_id=ana.id)), ("bia@exemplo.com", dict(atleta_id=bia.id)), ("paulo@exemplo.com", dict(professor_id=paulo.id))):
        svc.criar_conta(session, email, SENHA, **kw)
    session.commit()
    data = (inicio + timedelta(minutes=-180)).strftime("%d/%m")
    return dict(ana=ana.id, bia=bia.id, paulo=paulo.id, ativ=a1.id, data=data)


def _h(client, quem):
    r = client.post("/sessao", json={"email": f"{quem}@exemplo.com", "senha": SENHA})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _roteiro_feliz(mundo, texto=None):
    return [RespostaConversa(chamadas=(ChamadaFerramenta("c1", "listar_atividades", {"limite": 1}),)),
            texto or f"O seu último treino foi em {mundo['data']}, com 8,20 km em 47 min."]


def test_criar_conversa_responde_a_primeira_pergunta_com_link_do_treino(client, session, mundo, prov):
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    r = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "  Como foi o meu último treino?  "}, headers=_h(client, "ana"))
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["titulo"] == "Como foi o meu último treino?" and len(c["mensagens"]) == 1
    m = c["mensagens"][0]
    assert m["estado"] == "respondida" and m["motivo"] is None and m["ordem"] == 1 and "8,20 km" in m["texto"]
    assert m["links"] == [{"tipo": "treino", "rotulo": "Abrir treino", "atividade_id": mundo["ativ"], "serie_id": None, "data_texto": mundo["data"]}]
    gravada = session.query(Mensagem).one()  # uma linha por turno, com as ferramentas e os resultados
    assert gravada.estado == "respondida" and gravada.versao_checagens == "checagens_chat@1" and gravada.versao_prompt == "prompt_chat@3"
    assert gravada.chamadas_ferramenta[0]["nome"] == "listar_atividades" and gravada.chamadas_ferramenta[0]["resultado"]["total"] == 1
    assert (gravada.provedor, gravada.modelo) == ("falso", "falso-1")
    conv = session.query(Conversa).one()
    assert conv.atleta_id == mundo["ana"] and conv.dono_papel == "atleta"


def test_continuar_a_conversa_leva_o_historico_aprovado_ao_provedor(client, mundo, prov):
    h = _h(client, "ana")
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    cid = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Pergunta um?"}, headers=h).json()["id"]
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    r = client.post(f"/atletas/{mundo['ana']}/conversas/{cid}/mensagens", json={"pergunta": "Pergunta dois?"}, headers=h)
    assert r.status_code == 200 and r.json()["ordem"] == 2 and r.json()["estado"] == "respondida"
    enviadas = prov["falso"].recebidas[-2]  # primeira volta da segunda pergunta
    assert [m["content"] for m in enviadas if m["role"] == "user"] == ["Pergunta um?", "Pergunta dois?"]
    lista = client.get(f"/atletas/{mundo['ana']}/conversas", headers=h).json()
    assert [c["id"] for c in lista["conversas"]] == [cid]
    detalhe = client.get(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).json()
    assert [m["ordem"] for m in detalhe["mensagens"]] == [1, 2]


def test_apagar_conversa_leva_as_mensagens(client, session, mundo, prov):
    h = _h(client, "ana")
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    cid = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "oi?"}, headers=h).json()["id"]
    assert client.delete(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).status_code == 204
    assert client.get(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).status_code == 404
    assert session.query(Mensagem).count() == 0 and session.query(Conversa).count() == 0


def test_recusa_e_texto_fixo_e_nao_tem_link(client, mundo, prov):
    prov["falso"].roteiro = [RespostaConversa(chamadas=(ChamadaFerramenta("c1", "recusar", {"motivo": "fora_do_tema"}),))]
    m = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Receita de bolo?"}, headers=_h(client, "ana")).json()["mensagens"][0]
    assert m["estado"] == "recusada" and m["motivo"] == "fora_do_tema" and m["texto"].startswith("Eu respondo perguntas sobre os seus treinos") and m["links"] == []


def test_resposta_reprovada_nao_e_gravada_nem_devolvida(client, session, mundo, prov):
    ruim = "Você correu 99 km por causa do calor."
    prov["falso"].roteiro = _roteiro_feliz(mundo, ruim) + [ruim]
    m = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Como foi?"}, headers=_h(client, "ana")).json()["mensagens"][0]
    assert m["estado"] == "reprovada" and m["motivo"] and m["texto"] == FRASE_ERRO and "99" not in json.dumps({k: v for k, v in m.items() if k != "criada_em"})  # o horario pode ter "99" nos microssegundos
    g = session.query(Mensagem).one()
    assert g.resposta is None and g.estado == "reprovada" and "99" not in json.dumps([g.resposta, g.motivo])


def test_erro_do_provedor_vira_estado_erro_com_a_frase_fixa(client, session, mundo, prov):
    prov["falso"].roteiro = [ErroProvedor()]
    r = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=_h(client, "ana"))
    m = r.json()["mensagens"][0]
    assert r.status_code == 201 and (m["estado"], m["motivo"], m["texto"]) == ("erro", "provedor_erro", FRASE_ERRO)
    assert session.query(Mensagem).one().resposta is None  # a pergunta fica guardada; o atleta pode repetir


def test_conversa_de_outro_e_inexistente_dao_o_mesmo_404(client, mundo, prov):
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    cid = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=_h(client, "ana")).json()["id"]
    h = _h(client, "bia")
    for metodo, url, corpo in (("get", f"/atletas/{mundo['bia']}/conversas/{cid}", None), ("delete", f"/atletas/{mundo['bia']}/conversas/{cid}", None),
                               ("post", f"/atletas/{mundo['bia']}/conversas/{cid}/mensagens", {"pergunta": "oi?"})):
        alheia = client.request(metodo.upper(), url, headers=h, json=corpo)
        nenhuma = client.request(metodo.upper(), url.replace(f"/{cid}", "/999999"), headers=h, json=corpo)
        assert alheia.status_code == nenhuma.status_code == 404 and alheia.content == nenhuma.content, url
    assert client.get(f"/atletas/{mundo['bia']}/conversas", headers=h).json()["conversas"] == []  # a lista da Bia nao tem a da Ana
    # Bia pedindo pelo caminho da Ana: o id do caminho nao e o da sessao
    assert client.get(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).status_code == 404


def test_professor_com_vinculo_e_consentimento_recebe_404(client, mundo, prov):
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    cid = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=_h(client, "ana")).json()["id"]
    h = _h(client, "paulo")
    for url in (f"/atletas/{mundo['ana']}/conversas", f"/atletas/{mundo['ana']}/conversas/{cid}"):
        assert client.get(url, headers=h).status_code == 404
    assert client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "x"}, headers=h).status_code == 404
    assert client.delete(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).status_code == 404


@pytest.mark.parametrize("corpo", [{}, {"pergunta": ""}, {"pergunta": "   "}, {"pergunta": "x" * 1001}, {"pergunta": 3}, {"pergunta": MARCA * 200}])
def test_422_nao_repete_o_que_foi_enviado(client, mundo, corpo):
    r = client.post(f"/atletas/{mundo['ana']}/conversas", json=corpo, headers=_h(client, "ana"))
    assert r.status_code == 422 and MARCA not in r.text and "input" not in r.text


def test_limite_de_20_perguntas_por_hora_com_espere_s(client, session, mundo, prov):
    h = _h(client, "ana")
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    cid = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=h).json()["id"]
    for i in range(PERGUNTAS_POR_HORA - 1):
        session.add(Mensagem(conversa_id=cid, ordem=10 + i, pergunta="p", chamadas_ferramenta=[], resposta=None, estado="erro", motivo="provedor_erro",
                             versao_checagens="checagens_chat@1", versao_prompt="prompt_chat@3", criada_em=AGORA - timedelta(minutes=30)))
    session.commit()
    antes = prov["falso"].chamadas
    r = client.post(f"/atletas/{mundo['ana']}/conversas/{cid}/mensagens", json={"pergunta": "mais uma?"}, headers=h)
    assert r.status_code == 429 and 1 <= r.json()["espere_s"] <= 1830 and r.headers["retry-after"] == str(r.json()["espere_s"])
    assert r.json()["detail"] == "Você fez 20 perguntas na última hora."
    from app.rotas.chat import espere_texto
    assert r.json()["espere_texto"] == espere_texto(r.json()["espere_s"])  # nao depende do relogio: so confere que o texto vem do `espere_s`
    assert prov["falso"].chamadas == antes  # nem chegou ao provedor
    assert client.post(f"/atletas/{mundo['bia']}/conversas", json={"pergunta": "oi?"}, headers=_h(client, "bia")).status_code != 429  # o limite e por atleta


def test_nada_da_pergunta_vai_para_log(client, mundo, prov, caplog):
    caplog.set_level(logging.DEBUG)
    prov["falso"].roteiro = [ErroProvedor()]
    client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": f"Pergunta {MARCA}?"}, headers=_h(client, "ana"))
    assert MARCA not in caplog.text


@pytest.mark.parametrize("espere_s,texto", [(1, "1 min"), (59, "1 min"), (60, "1 min"), (61, "2 min"), (720, "12 min"), (721, "13 min"), (1799, "30 min"), (1800, "30 min"), (3600, "60 min")])
def test_espere_texto_em_minutos_para_cima(espere_s, texto):
    from app.rotas.chat import espere_texto
    assert espere_texto(espere_s) == f"Você pode perguntar de novo em {texto}."


def test_pedido_de_mudanca_sem_professor_so_a_primeira_frase_e_com_professor_as_duas(client, mundo, prov):
    pedido = [RespostaConversa(chamadas=(ChamadaFerramenta("c1", "recusar", {"motivo": "pedido_de_mudanca"}),))]
    prov["falso"].roteiro = list(pedido)
    com = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Monte meu treino?"}, headers=_h(client, "ana")).json()["mensagens"][0]
    prov["falso"].roteiro = list(pedido)
    sem = client.post(f"/atletas/{mundo['bia']}/conversas", json={"pergunta": "Monte meu treino?"}, headers=_h(client, "bia")).json()["mensagens"][0]
    from app.chat.recusa import RECUSA_MUDANCA_COM_PROFESSOR, RECUSA_MUDANCA_SEM_PROFESSOR
    assert com["texto"] == RECUSA_MUDANCA_COM_PROFESSOR  # a Ana tem professor vinculado
    assert sem["texto"] == RECUSA_MUDANCA_SEM_PROFESSOR and sem["estado"] == "recusada"  # a Bia nao tem
    assert RECUSA_MUDANCA_COM_PROFESSOR.startswith(RECUSA_MUDANCA_SEM_PROFESSOR) and RECUSA_MUDANCA_COM_PROFESSOR != RECUSA_MUDANCA_SEM_PROFESSOR


def test_link_do_treino_traz_a_data_como_veio_da_ferramenta(client, mundo, prov):
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    m = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Como foi?"}, headers=_h(client, "ana")).json()["mensagens"][0]
    assert m["links"][0]["data_texto"] == mundo["data"]


def test_429_do_provedor_mostra_a_frase_de_servico_ocupado(client, session, mundo, prov, monkeypatch):
    from app.chat import laco
    from app.rotas.chat import FRASE_OCUPADO
    monkeypatch.setattr(laco.time, "sleep", lambda _s: None)  # sem esperar de verdade
    prov["falso"].roteiro = [LimiteDoProvedor(), LimiteDoProvedor()]
    r = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=_h(client, "ana"))
    m = r.json()["mensagens"][0]
    assert r.status_code == 201 and (m["estado"], m["motivo"], m["texto"]) == ("erro", "provedor_limite", FRASE_OCUPADO)
    assert FRASE_OCUPADO == "O serviço de IA está ocupado. Tente de novo em 1 minuto." and session.query(Mensagem).one().resposta is None
    assert client.get(f"/atletas/{mundo['ana']}/conversas/{r.json()['id']}", headers=_h(client, "ana")).json()["mensagens"][0]["texto"] == FRASE_OCUPADO
