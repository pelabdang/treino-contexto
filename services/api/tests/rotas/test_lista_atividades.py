"""`GET /atletas/{id}/atividades`: a lista de treinos, por cursor (UX: aba Treinos e tela inicial). Dados sinteticos."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Assessoria, Atividade, Atleta, CheckinTreino, FeedbackTreino
from app.db.session import get_session
from app.main import criar_app
from app.servicos import conta as svc_conta
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.acesso_de_teste import sem_login

SENHA = "senha-de-teste-123"
AGORA = datetime.now(timezone.utc).replace(microsecond=0)
OBS = "observacao-sintetica-que-nao-pode-sair"
TEXTO_FB = "texto-de-feedback-sintetico-que-nao-pode-sair"


@pytest.fixture
def app(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    return a


@pytest.fixture
def client(app):
    return TestClient(sem_login(app))


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


def _ativ(session, atleta, n, dias_atras, modalidade="corrida", dur=1800.0, dist=5000.0, horas=0, **kw):
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=str(n), modalidade=modalidade, inicio=AGORA - timedelta(days=dias_atras, hours=horas),
                  duracao_s=dur, distancia_m=dist, fuso_min=-180, **kw)
    session.add(a)
    session.flush()
    return a


def _checkin(session, a, com_feedback=None):
    ck = CheckinTreino(atividade_id=a.id, pse=5, sensacao=3, nada_a_relatar=False, dor=True, cansaco=False, sono_ruim=False, calor=False,
                       trabalho_estresse=False, texto=OBS, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA)
    session.add(ck)
    session.flush()
    if com_feedback:
        session.add(FeedbackTreino(checkin_id=ck.id, estado="pronto", texto=TEXTO_FB, versao_fatos="fatos_treino@2", versao_prompt="p",
                                   versao_checagens="c", provedor="falso", modelo="falso", tentativas=1, checkin_atualizado_em=AGORA,
                                   tentado_em=AGORA))
    return ck


def _lista(client, atleta, **params):
    r = client.get(f"/atletas/{atleta.id}/atividades", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_ordem_mais_recente_primeiro_e_campos_do_item(client, session, atleta):
    antiga = _ativ(session, atleta, 1, 5, dur=1800, dist=5000)
    recente = _ativ(session, atleta, 2, 1, "ciclismo", dur=3600, dist=30000, subtipo=None, tipo_treino="longo", tipo_origem="sugestao")
    session.commit()
    j = _lista(client, atleta)
    assert [i["atividade_id"] for i in j["itens"]] == [recente.id, antiga.id] and j["proximo"] is None and j["limite"] == 20
    i = j["itens"][0]
    assert (i["modalidade"], i["tipo_treino"], i["duracao"], i["distancia"], i["destaque"]) == ("ciclismo", "longo", "1:00:00", "30,00 km", "Velocidade média 30,0 km/h")
    assert i["data_local"] and len(i["hora_local"]) == 5
    c = j["itens"][1]
    assert (c["destaque"], c["distancia"], c["duracao"]) == ("Pace médio 6:00 /km", "5,00 km", "0:30:00")
    assert (c["checkin_estado"], c["feedback_estado"]) == ("pendente", "sem_checkin")  # 5 dias: ainda dentro do prazo de 7


def test_paginacao_por_cursor_nao_repete_nem_pula_inclusive_com_o_mesmo_inicio(client, session, atleta):
    ids = []
    for n in range(7):
        ids.append(_ativ(session, atleta, n, 1 + n // 2).id)  # pares de atividades com o MESMO inicio
    session.commit()
    esperado = [a.id for a in session.query(Atividade).order_by(Atividade.inicio.desc(), Atividade.id.desc())]
    vistos, cursor, paginas = [], None, 0
    while True:
        params = {"limite": 3} | ({"antes_de": cursor} if cursor else {})
        j = _lista(client, atleta, **params)
        vistos += [i["atividade_id"] for i in j["itens"]]
        paginas += 1
        cursor = j["proximo"]
        if cursor is None:
            break
    assert vistos == esperado and len(set(vistos)) == 7 and paginas == 3


def test_atividade_nova_no_topo_nao_desloca_a_proxima_pagina(client, session, atleta):
    for n in range(4):
        _ativ(session, atleta, n, 2 + n)
    session.commit()
    p1 = _lista(client, atleta, limite=2)
    _ativ(session, atleta, 99, 0, horas=1)  # chegou depois de a pagina 1 ser lida
    session.commit()
    p2 = _lista(client, atleta, limite=2, antes_de=p1["proximo"])
    assert [i["atividade_id"] for i in p2["itens"]] == [a.id for a in session.query(Atividade).filter(Atividade.fonte_id.in_(["2", "3"])).order_by(Atividade.inicio.desc())]


def test_limite_padrao_maximo_e_invalidos(client, session, atleta):
    for n in range(25):
        _ativ(session, atleta, n, n)
    session.commit()
    assert len(_lista(client, atleta)["itens"]) == 20
    assert len(_lista(client, atleta, limite=100)["itens"]) == 25
    for ruim in (0, 101, -1, "abc"):
        assert client.get(f"/atletas/{atleta.id}/atividades", params={"limite": ruim}).status_code == 422
    r = client.get(f"/atletas/{atleta.id}/atividades", params={"antes_de": "lixo-qualquer"})
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == "cursor_invalido"


def test_filtro_de_modalidade(client, session, atleta):
    _ativ(session, atleta, 1, 1, "corrida")
    nat = _ativ(session, atleta, 2, 2, "natacao", dist=1800)
    session.commit()
    j = _lista(client, atleta, modalidade="natacao")
    assert [i["atividade_id"] for i in j["itens"]] == [nat.id] and j["itens"][0]["distancia"] == "1.800 m" and j["itens"][0]["destaque"] is None
    assert client.get(f"/atletas/{atleta.id}/atividades", params={"modalidade": "voo"}).status_code == 422


def test_checkin_pendente_so_elegivel_sem_checkin_e_no_prazo(client, session, atleta):
    pendente = _ativ(session, atleta, 1, 1)
    feito = _ativ(session, atleta, 2, 1, horas=3)
    _checkin(session, feito)
    _ativ(session, atleta, 3, 40)  # fora do prazo (vencido)
    _ativ(session, atleta, 4, 1, horas=5, subtipo="multiesporte_pai")  # nao pede check-in
    _ativ(session, atleta, 5, 1, horas=6, subtipo="troca")
    session.commit()
    j = _lista(client, atleta, checkin_pendente="true")
    assert [i["atividade_id"] for i in j["itens"]] == [pendente.id] and j["itens"][0]["checkin_estado"] == "pendente"
    todos = {i["atividade_id"]: i["checkin_estado"] for i in _lista(client, atleta)["itens"]}
    assert sorted(todos.values()) == ["feito", "nao_se_aplica", "nao_se_aplica", "pendente", "vencido"]


def test_checkin_pendente_tambem_pagina(client, session, atleta):
    for n in range(5):
        _ativ(session, atleta, n, 1, horas=n)
    session.commit()
    p1 = _lista(client, atleta, checkin_pendente="true", limite=2)
    p2 = _lista(client, atleta, checkin_pendente="true", limite=2, antes_de=p1["proximo"])
    p3 = _lista(client, atleta, checkin_pendente="true", limite=2, antes_de=p2["proximo"])
    ids = [i["atividade_id"] for p in (p1, p2, p3) for i in p["itens"]]
    assert len(ids) == 5 == len(set(ids)) and p3["proximo"] is None


def test_estados_do_feedback_e_nada_de_texto_de_saude_na_lista(client, session, atleta):
    sem = _ativ(session, atleta, 1, 1)
    so_checkin = _ativ(session, atleta, 2, 2)
    _checkin(session, so_checkin)
    pronto = _ativ(session, atleta, 3, 3)
    _checkin(session, pronto, com_feedback=True)
    pai = _ativ(session, atleta, 4, 4, subtipo="multiesporte_pai")
    session.commit()
    r = client.get(f"/atletas/{atleta.id}/atividades")
    estados = {i["atividade_id"]: (i["checkin_estado"], i["feedback_estado"]) for i in r.json()["itens"]}
    assert estados == {sem.id: ("pendente", "sem_checkin"), so_checkin.id: ("feito", "pendente"), pronto.id: ("feito", "pronto"),
                       pai.id: ("nao_se_aplica", None)}
    assert OBS not in r.text and TEXTO_FB not in r.text  # o texto fica no GET da atividade, do proprio atleta
    for proibido in ("texto", "pse", "sensacao", "fc_media", "clima", "carga", "inicio_lat"):
        assert proibido not in json.dumps(r.json()["itens"][0]), proibido


def test_pronto_vira_desatualizado_pelo_tipo_na_propria_lista(client, session, atleta):
    a = _ativ(session, atleta, 1, 1, tipo_treino="leve", tipo_origem="sugestao")
    ck = _checkin(session, a, com_feedback=True)
    session.flush()
    fb = session.query(FeedbackTreino).one()
    fb.tipo_visto = "leve"
    session.commit()
    assert _lista(client, atleta)["itens"][0]["feedback_estado"] == "pronto"
    a.tipo_treino = "longo"  # o professor corrigiu
    session.commit()
    assert _lista(client, atleta)["itens"][0]["feedback_estado"] == "desatualizado"


def test_sem_n_mais_1_o_numero_de_consultas_nao_cresce_com_o_numero_de_treinos(client, session, engine):
    def consultas(nome, n_treinos):
        at = Atleta(nome=nome)
        session.add(at)
        session.flush()
        for n in range(n_treinos):
            a = _ativ(session, at, n, n)
            _checkin(session, a, com_feedback=(n % 2 == 0))
        session.commit()
        session.expire_all()
        contagem = []

        def conta(*_a, **_k):
            contagem.append(1)

        event.listen(engine, "before_cursor_execute", conta)
        try:
            _lista(client, at, limite=100)
        finally:
            event.remove(engine, "before_cursor_execute", conta)
        return len(contagem)

    pequena, grande = consultas("Atleta Pequeno", 3), consultas("Atleta Grande", 30)
    assert grande - pequena <= 1, (pequena, grande)  # a pagina toda vem junta, nao uma consulta por treino


# ---------- acesso (sessao de verdade) ----------

def test_so_o_atleta_dono_lista_os_proprios_treinos(session, app, atleta):
    ass = Assessoria(nome="Assessoria Teste")
    session.add(ass)
    session.flush()
    outro = Atleta(nome="Outro Ficticio", assessoria_id=ass.id)
    session.add(outro)
    session.flush()
    _ativ(session, atleta, 1, 1)
    svc_conta.criar_conta(session, "dono@exemplo.com", SENHA, atleta_id=atleta.id)
    svc_conta.criar_conta(session, "outro@exemplo.com", SENHA, atleta_id=outro.id)
    session.commit()
    c = TestClient(app)  # sem o helper: sessao de verdade
    url = f"/atletas/{atleta.id}/atividades"
    assert c.get(url).status_code == 401

    def h(email):
        return {"Authorization": "Bearer " + c.post("/sessao", json={"email": email, "senha": SENHA}).json()["token"]}

    assert c.get(url, headers=h("dono@exemplo.com")).status_code == 200
    alheio = c.get(url, headers=h("outro@exemplo.com"))
    inexistente = c.get("/atletas/999999/atividades", headers=h("outro@exemplo.com"))
    assert alheio.status_code == 404 and alheio.content == inexistente.content


def test_exemplo_sintetico_da_resposta(client, session, atleta, capsys):
    a = _ativ(session, atleta, 1, 1, dur=3010, dist=10000, tipo_treino="moderado", tipo_origem="sugestao")
    _checkin(session, a, com_feedback=True)
    _ativ(session, atleta, 2, 3, "ciclismo", dur=5400, dist=42000)
    session.commit()
    j = _lista(client, atleta, limite=2)
    assert set(j) == {"atleta_id", "limite", "itens", "proximo"} and len(j["itens"]) == 2
