"""Perguntas prontas escolhidas pela API e 👍/👎 na resposta (adendo 17 da ADR 0004). Sessao de verdade, tudo sintetico."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from app.chat import perguntas_prontas as pp
from app.chat.registro import REGISTRO
from app.db.models import Atividade, Atleta, CargaAtividade, CheckinTreino, Mensagem, RecuperacaoDia
from app.llm.camada import ChamadaFerramenta, ErroProvedor, RespostaConversa
from app.rotas.chat import PERGUNTAS_POR_HORA  # noqa: F401
from app.servicos.checkin import hoje_local

from tests.rotas.test_chat import _h, _roteiro_feliz, app, client, mundo, prov  # noqa: F401

AGORA = datetime.now(timezone.utc)


def _ativ(session, atleta_id, dias, modalidade="corrida", tipo="leve", n=[0]):
    n[0] += 1
    a = Atividade(atleta_id=atleta_id, fonte="t", fonte_id=f"x{n[0]}", modalidade=modalidade, inicio=AGORA.replace(hour=15, minute=0, second=0, microsecond=0) - timedelta(days=dias),
                  fuso_min=-180, duracao_s=2400.0, distancia_m=7000.0, tipo_treino=tipo)
    session.add(a)
    session.flush()
    return a


def _textos(client, atleta_id, quem="ana"):
    r = client.get(f"/atletas/{atleta_id}/chat/perguntas-prontas", headers=_h(client, quem))
    assert r.status_code == 200
    return [p["texto"] for p in r.json()["perguntas"]]


@pytest.fixture
def novo(session):
    """Atleta sem nenhum dado (nao entra no `mundo`, que ja tem um treino da Ana)."""
    a = Atleta(nome="Cris Teste")
    session.add(a)
    session.commit()
    return a.id


def test_catalogo_so_tem_frases_que_cabem_numa_ferramenta():
    ids = [p.id for p in pp.CATALOGO]
    assert len(set(ids)) == len(ids) and len({p.texto for p in pp.CATALOGO}) == len(ids)
    for p in pp.CATALOGO:
        assert p.ferramentas and set(p.ferramentas) <= set(REGISTRO), p.id
        assert p.texto.endswith("?") and len(p.texto) <= 60 and "\n" not in p.texto


def test_atleta_sem_dado_nao_recebe_pergunta(client, session, mundo):  # noqa: F811
    from app.servicos import conta as svc
    a = Atleta(nome="Cris Teste")
    session.add(a)
    session.flush()
    svc.criar_conta(session, "cris@exemplo.com", "senha-de-teste-123", atleta_id=a.id)
    session.commit()
    r = client.get(f"/atletas/{a.id}/chat/perguntas-prontas", headers=_h(client, "cris"))
    assert r.status_code == 200 and r.json() == {"versao": "perguntas_prontas@1", "atleta_id": a.id, "perguntas": []}


def test_so_sugere_o_que_o_atleta_tem_e_na_ordem_do_catalogo(client, session, mundo):  # noqa: F811
    ana = mundo["ana"]  # ja tem 1 corrida leve ha 2 dias
    assert _textos(client, ana) == ["Como foi o meu último treino?", "Qual foi o meu treino mais longo este ano?"]
    for d in (3, 5, 9, 10):  # corridas leves e dois intervalados
        _ativ(session, ana, d)
    _ativ(session, ana, 12, tipo="intervalado")
    _ativ(session, ana, 14, tipo="intervalado")
    session.commit()
    t = _textos(client, ana)
    assert t[:4] == ["Como foi o meu último treino?", "Como foi esta semana comparada com a passada?", "Meu pace nos treinos leves melhorou no último mês?",
                     "Meus tiros estão ficando mais rápidos?"]
    assert "natação" not in " ".join(t) and "ciclismo" not in " ".join(t) and "sono" not in " ".join(t)  # sem treino dessas modalidades nem noites


def test_natacao_e_ciclismo_so_com_treino_nas_ultimas_8_semanas(client, session, mundo):  # noqa: F811
    ana = mundo["ana"]
    for d in (1, 8, 15):
        _ativ(session, ana, d, "natacao", None)
    _ativ(session, ana, 30, "ciclismo", None)
    _ativ(session, ana, 90, "ciclismo", None)  # fora da janela
    session.commit()
    t = _textos(client, ana)
    assert "Como está o meu ritmo na natação?" in t and "Como foi o meu último treino de ciclismo?" in t
    session.query(Atividade).filter(Atividade.modalidade == "ciclismo").delete()
    session.commit()
    assert "Como foi o meu último treino de ciclismo?" not in _textos(client, ana)
    session.query(Atividade).filter(Atividade.atleta_id == ana, Atividade.modalidade == "natacao", Atividade.inicio < AGORA - timedelta(days=10)).delete()
    session.commit()
    assert "Como está o meu ritmo na natação?" not in _textos(client, ana)  # sobraram 1 treino de natação: menos de 3


def test_sono_checkin_de_ontem_e_forma_dependem_do_dado(client, session, mundo):  # noqa: F811
    ana = mundo["ana"]
    hoje = hoje_local()
    ontem = _ativ(session, ana, 1)
    session.add(CheckinTreino(atividade_id=ontem.id, pse=4, sensacao=4, nada_a_relatar=True, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA))
    session.add(RecuperacaoDia(atleta_id=ana, origem="garmin_connect", noite=hoje, sono_s=25000, versao_leitura="recuperacao@1", importado_em=AGORA))
    session.add(CargaAtividade(atividade_id=ontem.id, estado="calculada", carga=50.0, metodo="rtss", cobertura_pct=100.0, granularidade="atividade", entrada="x",
                               versao="carga@2", calculado_em=AGORA))
    session.commit()
    t = _textos(client, ana)
    assert "Como foi o check-in de ontem?" in t and "Como está a minha forma hoje?" in t and "Como foi o meu sono na última noite?" in t
    assert len(t) <= 6 and t == [p.texto for p in pp.CATALOGO if p.texto in t]  # ordem do catalogo


def test_no_maximo_6_ordem_estavel_e_sem_aleatorio(client, session, mundo):  # noqa: F811
    ana = mundo["ana"]
    for d in (1, 2, 3, 4, 5, 6, 7):
        _ativ(session, ana, d)
        _ativ(session, ana, d, "natacao", None)
        _ativ(session, ana, d, "corrida", "intervalado")
    session.commit()
    primeira = _textos(client, ana)
    assert len(primeira) == 6 and all(_textos(client, ana) == primeira for _ in range(5))


def test_so_o_dono_ve_as_perguntas_prontas(client, mundo):  # noqa: F811
    url = f"/atletas/{mundo['ana']}/chat/perguntas-prontas"
    assert client.get(url).status_code == 401
    for quem in ("bia", "paulo"):  # outro atleta e o professor (com vinculo): o mesmo 404 de atleta inexistente
        h = _h(client, quem)
        assert client.get(url, headers=h).status_code == 404
        assert client.get(url, headers=h).content == client.get("/atletas/999999/chat/perguntas-prontas", headers=h).content


# --- avaliacao ---------------------------------------------------------------------------------------------------------------------

def _conversa(client, mundo, prov, quem="ana"):  # noqa: F811
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    c = client.post(f"/atletas/{mundo[quem]}/conversas", json={"pergunta": "Como foi?"}, headers=_h(client, quem)).json()
    return c["id"], c["mensagens"][0]["id"]


def _url(mundo, cid, mid, quem="ana"):  # noqa: F811
    return f"/atletas/{mundo[quem]}/conversas/{cid}/mensagens/{mid}/avaliacao"


def test_avaliar_desfazer_e_trocar(client, session, mundo, prov):  # noqa: F811
    cid, mid = _conversa(client, mundo, prov)
    h = _h(client, "ana")
    r = client.put(_url(mundo, cid, mid), json={"valor": 1}, headers=h)
    assert r.status_code == 200 and r.json()["avaliacao"] == 1
    m = session.get(Mensagem, mid)
    session.refresh(m)
    assert m.avaliacao == 1 and m.avaliada_em is not None
    assert client.put(_url(mundo, cid, mid), json={"valor": -1}, headers=h).json()["avaliacao"] == -1
    assert client.get(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).json()["mensagens"][0]["avaliacao"] == -1  # aparece no GET
    r = client.put(_url(mundo, cid, mid), json={"valor": None}, headers=h)
    assert r.status_code == 200 and r.json()["avaliacao"] is None
    session.refresh(m)
    assert m.avaliacao is None and m.avaliada_em is None


@pytest.mark.parametrize("corpo", [{}, {"valor": 0}, {"valor": 2}, {"valor": "1"}, {"valor": True}, {"valor": 1, "texto": "otimo"}, []])
def test_valor_invalido_da_422_sem_eco(client, mundo, prov, corpo):  # noqa: F811
    cid, mid = _conversa(client, mundo, prov)
    r = client.put(_url(mundo, cid, mid), json=corpo, headers=_h(client, "ana"))
    assert r.status_code == 422 and "otimo" not in r.text and '"input"' not in r.text


def test_a_mensagem_nao_tem_coluna_de_texto_livre_da_avaliacao():
    assert {c.name for c in Mensagem.__table__.columns if "avalia" in c.name} == {"avaliacao", "avaliada_em"}


@pytest.mark.parametrize("roteiro,estado", [([ErroProvedor()], "erro"),
                                            ([RespostaConversa(chamadas=(ChamadaFerramenta("c", "recusar", {"motivo": "fora_do_tema"}),))], "recusada")])
def test_so_a_respondida_pode_ser_avaliada(client, mundo, prov, roteiro, estado):  # noqa: F811
    prov["falso"].roteiro = roteiro
    c = client.post(f"/atletas/{mundo['ana']}/conversas", json={"pergunta": "Oi?"}, headers=_h(client, "ana")).json()
    m = c["mensagens"][0]
    assert m["estado"] == estado
    r = client.put(_url(mundo, c["id"], m["id"]), json={"valor": 1}, headers=_h(client, "ana"))
    assert r.status_code == 409


def test_avaliacao_de_outro_e_inexistente_dao_o_mesmo_404(client, mundo, prov):  # noqa: F811
    cid, mid = _conversa(client, mundo, prov)
    h = _h(client, "bia")
    caminhos = {"alheia": _url(mundo, cid, mid, "bia"), "mensagem inexistente": _url(mundo, cid, 999999, "bia"),
                "conversa inexistente": _url(mundo, 999999, mid, "bia")}
    for nome, url in caminhos.items():
        assert client.put(url, json={"valor": 1}, headers=h).status_code == 404, nome
    assert client.put(f"/atletas/{mundo['ana']}/conversas/{cid}/mensagens/{mid}/avaliacao", json={"valor": 1}, headers=h).status_code == 404  # id de outro no caminho
    assert client.put(_url(mundo, cid, mid), json={"valor": 1}, headers=_h(client, "paulo")).status_code == 404  # professor
    assert client.put(_url(mundo, cid, mid), json={"valor": 1}).status_code == 401
    # a mensagem da Ana continua sem avaliacao
    assert client.get(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=_h(client, "ana")).json()["mensagens"][0]["avaliacao"] is None


def test_avaliacao_nao_vai_ao_provedor_e_some_com_a_conversa(client, session, mundo, prov):  # noqa: F811
    cid, mid = _conversa(client, mundo, prov)
    h = _h(client, "ana")
    client.put(_url(mundo, cid, mid), json={"valor": -1}, headers=h)
    prov["falso"].roteiro = _roteiro_feliz(mundo)
    client.post(f"/atletas/{mundo['ana']}/conversas/{cid}/mensagens", json={"pergunta": "E agora?"}, headers=h)
    enviado = json.dumps(prov["falso"].recebidas[-2], ensure_ascii=False)
    assert "avaliacao" not in enviado and '"-1"' not in enviado
    assert client.delete(f"/atletas/{mundo['ana']}/conversas/{cid}", headers=h).status_code == 204
    assert session.query(Mensagem).count() == 0
