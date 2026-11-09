"""PUT, GET e DELETE do check-in pos-treino (issue #296, ADR 0012). Dados sinteticos; o texto marcador nunca pode vazar."""

import logging
from datetime import date, datetime, timezone

import pytest
from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import get_session
from app.main import criar_app
from app.servicos import checkin as svc
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

MARCADOR = "MARCADOR-SINTETICO-123"
HOJE = date(2026, 11, 9)


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, raise_server_exceptions=False)


def _ativ(session, atleta_id, fonte_id="1", dia=date(2026, 11, 8), hora=10, modalidade="corrida", subtipo=None, fuso_min=-180):
    a = Atividade(atleta_id=atleta_id, fonte="teste", fonte_id=fonte_id, modalidade=modalidade, subtipo=subtipo,
                  inicio=datetime(dia.year, dia.month, dia.day, hora, tzinfo=timezone.utc), fuso_min=fuso_min, duracao_s=2700.0)
    session.add(a)
    session.commit()
    return a.id


@pytest.fixture
def ids(session):
    ana, beto = Atleta(nome="Ana"), Atleta(nome="Beto")
    session.add_all([ana, beto])
    session.commit()
    return ana.id, beto.id, _ativ(session, ana.id)


def corpo(**kw):
    c = {"pse": 6, "sensacao": 4, "nada_a_relatar": False, "atalhos": ["cansaco", "trabalho_estresse"], "texto": "Semana puxada."}
    c.update(kw)
    return {k: v for k, v in c.items() if v is not ...}


def url(atleta, atividade):
    return f"/atletas/{atleta}/atividades/{atividade}/checkin"


def test_grava_le_edita_e_apaga(client, ids, session):
    ana, _, a = ids
    r = client.put(url(ana, a), json=corpo())
    assert r.status_code == 200
    j = r.json()
    assert (j["atividade_id"], j["pse"], j["pse_texto"], j["sensacao"], j["sensacao_texto"]) == (a, 6, "6", 4, "bem")
    assert j["atalhos"] == [{"chave": "cansaco", "texto": "Cansaço"}, {"chave": "trabalho_estresse", "texto": "Trabalho ou estresse"}]
    assert (j["texto"], j["versao"], j["nada_a_relatar"]) == ("Semana puxada.", "checkin@1", False)
    assert j["registrado_em"].endswith("-03:00") and j["atualizado_em"].endswith("-03:00")
    assert client.get(url(ana, a)).json() == j

    r2 = client.put(url(ana, a), json=corpo(pse=5, atalhos=["calor"], texto=None))
    assert r2.status_code == 200
    j2 = r2.json()
    assert (j2["pse_texto"], [x["chave"] for x in j2["atalhos"]], j2["texto"]) == ("difícil", ["calor"], None)
    assert j2["registrado_em"] == j["registrado_em"] and j2["atualizado_em"] >= j["atualizado_em"]
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 1  # nunca dois

    assert client.delete(url(ana, a)).status_code == 204
    assert client.get(url(ana, a)).status_code == 404
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 0  # a linha sai, nao so os campos
    assert client.delete(url(ana, a)).status_code == 204  # idempotente


def test_nada_a_relatar_e_valido(client, ids):
    ana, _, a = ids
    r = client.put(url(ana, a), json={"pse": 0, "sensacao": 3, "nada_a_relatar": True})
    assert r.status_code == 200
    assert (r.json()["pse_texto"], r.json()["atalhos"], r.json()["texto"]) == ("repouso", [], None)


def test_put_substitui_tudo_e_atalho_ausente_desliga(client, ids, session):
    ana, _, a = ids
    client.put(url(ana, a), json=corpo(atalhos=["dor", "sono_ruim"], texto=None))
    client.put(url(ana, a), json=corpo(atalhos=["calor"], texto=None))
    c = session.scalars(select(CheckinTreino)).one()
    assert (c.dor, c.sono_ruim, c.calor, c.cansaco) == (False, False, True, False)


def test_texto_e_aparado_e_vazio_vira_nulo(client, ids):
    ana, _, a = ids
    assert client.put(url(ana, a), json=corpo(texto="  oi  ", atalhos=[])).json()["texto"] == "oi"
    r = client.put(url(ana, a), json=corpo(texto="   ", atalhos=["dor"]))
    assert r.status_code == 200 and r.json()["texto"] is None
    assert client.put(url(ana, a), json=corpo(texto="   ", atalhos=[])).status_code == 422  # sobrou nada: sem observacao


def test_texto_de_500_caracteres_passa_e_501_nao(client, ids):
    ana, _, a = ids
    assert client.put(url(ana, a), json=corpo(texto="x" * 500, atalhos=[])).status_code == 200
    assert client.put(url(ana, a), json=corpo(texto="x" * 501, atalhos=[])).status_code == 422


@pytest.mark.parametrize("mudanca", [
    {"pse": -1}, {"pse": 11}, {"pse": 5.5}, {"pse": "6"}, {"pse": True},
    {"sensacao": 0}, {"sensacao": 6},
    {"atalhos": ["desconhecido"]}, {"atalhos": ["dor", "dor"]},
    {"nada_a_relatar": True},  # com atalho e texto
    {"atalhos": [], "texto": None},  # sem nada e sem "nada a relatar"
    {"pse": ...}, {"sensacao": ...}, {"nada_a_relatar": ...},
])
def test_422_para_entrada_invalida(client, ids, session, mudanca):
    ana, _, a = ids
    r = client.put(url(ana, a), json=corpo(**mudanca))
    assert r.status_code == 422
    assert all(set(e) == {"loc", "msg", "type"} for e in r.json()["detail"])
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 0


def test_422_nao_repete_a_entrada_em_nenhum_cenario(client, ids, caplog):
    ana, _, a = ids
    caplog.set_level(logging.DEBUG)
    cenarios = [
        corpo(texto=MARCADOR + "x" * 500, atalhos=[]),  # longo demais
        corpo(pse=MARCADOR),  # tipo errado
        corpo(atalhos=[MARCADOR]),  # atalho desconhecido
        corpo(nada_a_relatar=True, texto=MARCADOR),  # incoerente
        corpo(sensacao=MARCADOR, texto=MARCADOR),
        {MARCADOR: MARCADOR},  # campos faltando e extras
    ]
    for c in cenarios:
        r = client.put(url(ana, a), json=c)
        assert r.status_code == 422
        assert MARCADOR not in r.text
        assert "input" not in r.text and "ctx" not in r.text
    r = client.put(url(ana, a), content=("{" + MARCADOR).encode(), headers={"content-type": "application/json"})  # JSON quebrado
    assert r.status_code == 422 and MARCADOR not in r.text
    assert MARCADOR not in caplog.text


def test_marcador_nao_vai_para_o_log_no_put_feliz_nem_no_500(client, ids, caplog, monkeypatch):
    ana, _, a = ids
    caplog.set_level(logging.DEBUG)
    assert client.put(url(ana, a), json=corpo(texto=MARCADOR)).status_code == 200
    assert "checkin gravado" in caplog.text and MARCADOR not in caplog.text

    def quebra(*args, **kw):
        raise RuntimeError(f"[parameters: ('{MARCADOR}',)]")  # como um erro de banco que carrega os parametros

    monkeypatch.setattr(svc, "gravar_checkin", quebra)
    r = client.put(url(ana, a), json=corpo(texto=MARCADOR))
    assert r.status_code == 500 and MARCADOR not in r.text
    assert MARCADOR not in caplog.text


def test_outras_rotas_da_api_continuam_com_o_422_padrao(client, ids):
    ana, _, a = ids
    r = client.get("/atletas/abc/atividades/1")
    assert r.status_code == 422 and "input" in r.text  # o handler novo e so do check-in


def test_404_atleta_ou_atividade_de_outro_atleta_nas_tres_rotas(client, ids, session):
    ana, beto, a = ids
    for metodo, kw in (("put", {"json": corpo()}), ("get", {}), ("delete", {})):
        assert getattr(client, metodo)(url(beto, a), **kw).status_code == 404  # atividade da Ana pelo Beto
        assert getattr(client, metodo)(url(999, a), **kw).status_code == 404
        assert getattr(client, metodo)(url(ana, 999), **kw).status_code == 404
    client.put(url(ana, a), json=corpo())
    assert client.delete(url(beto, a)).status_code == 404
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 1  # o do Beto nao apagou o da Ana


def test_422_sem_vazamento_vence_o_404(client, ids):
    assert client.put(url(999, 999), json=corpo(pse=99)).status_code == 422


@pytest.mark.parametrize("subtipo", ["multiesporte_pai", "troca"])
def test_multiesporte_pai_e_troca_nao_pedem_checkin(client, ids, session, subtipo):
    ana, _, _ = ids
    a = _ativ(session, ana, "m", subtipo=subtipo, modalidade="outra")
    r = client.put(url(ana, a), json=corpo())
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == "atividade_sem_checkin"


def test_cada_parte_do_multiesporte_e_forca_tem_o_seu(client, ids, session):
    ana, _, _ = ids
    partes = [_ativ(session, ana, f"p{i}", modalidade=m) for i, m in enumerate(["natacao", "ciclismo", "corrida", "outra"])]
    assert all(client.put(url(ana, p), json=corpo()).status_code == 200 for p in partes)
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 4


@pytest.mark.parametrize("dia,hora,fuso,esperado", [
    (date(2026, 11, 2), 12, -180, 200),  # 7 dias antes: ainda vale
    (date(2026, 11, 1), 12, -180, 422),  # 8 dias antes
    (date(2026, 11, 2), 2, -180, 422),   # 02:00 UTC = 23:00 de 01/11 local: 8 dias
    (date(2026, 11, 2), 3, -180, 200),   # 03:00 UTC = 00:00 de 02/11 local: a borda
    (date(2026, 11, 2), 2, None, 422),   # sem fuso: America/Sao_Paulo (UTC-3), mesmo resultado
    (date(2026, 11, 2), 3, None, 200),
    (date(2026, 11, 9), 12, -180, 200),  # hoje
])
def test_prazo_de_7_dias_pela_data_local(client, ids, session, dia, hora, fuso, esperado):
    ana, _, _ = ids
    a = _ativ(session, ana, "p", dia=dia, hora=hora, fuso_min=fuso)
    r = client.put(url(ana, a), json=corpo())
    assert r.status_code == esperado
    if esperado == 422:
        assert r.json()["detail"][0]["type"] == "fora_do_prazo"
        assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 0


def test_editar_nao_tem_prazo(client, ids, session, monkeypatch):
    ana, _, a = ids
    assert client.put(url(ana, a), json=corpo()).status_code == 200
    monkeypatch.setattr(svc, "hoje_local", lambda: date(2027, 6, 1))  # meses depois
    assert client.put(url(ana, a), json=corpo(pse=7)).status_code == 200
    assert client.get(url(ana, a)).json()["pse"] == 7
    assert client.delete(url(ana, a)).status_code == 204


def test_prazo_e_parametro_facil_de_mudar(client, ids, session, monkeypatch):
    ana, _, _ = ids
    a = _ativ(session, ana, "velha", dia=date(2026, 10, 20))
    assert client.put(url(ana, a), json=corpo()).status_code == 422
    monkeypatch.setattr(svc, "PRAZO_DIAS", 30)
    assert client.put(url(ana, a), json=corpo()).status_code == 200


def test_quais_treinos_pedem_checkin_e_parametro(client, ids, session, monkeypatch):
    ana, _, _ = ids
    a = _ativ(session, ana, "forca", modalidade="outra", subtipo="forca")
    monkeypatch.setattr(svc, "SUBTIPOS_SEM_CHECKIN", frozenset({"forca"}))
    assert client.put(url(ana, a), json=corpo()).status_code == 422


def test_put_simultaneo_da_mesma_atividade_vira_atualizacao(ids, session, monkeypatch):
    """O outro PUT ganhou a corrida: a busca diz que nao existe, o INSERT ON CONFLICT nao insere, a nova busca acha e atualiza."""
    ana, _, a = ids
    ativ = session.get(Atividade, a)
    original = svc._buscar
    estado = {"n": 0}

    def buscar(sess, atividade_id):
        estado["n"] += 1
        if estado["n"] == 1:
            sess.add(CheckinTreino(atividade_id=atividade_id, pse=1, sensacao=1, nada_a_relatar=True, versao="checkin@1",
                                   registrado_em=datetime(2026, 11, 9, tzinfo=timezone.utc),
                                   atualizado_em=datetime(2026, 11, 9, tzinfo=timezone.utc)))
            sess.flush()
            return None
        return original(sess, atividade_id)

    monkeypatch.setattr(svc, "_buscar", buscar)
    c = svc.gravar_checkin(session, ativ, svc.DadosCheckin(8, 2, False, ("dor",), None))
    assert (c.pse, c.dor, c.nada_a_relatar) == (8, True, False)
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 1


def test_dois_put_de_verdade_ao_mesmo_tempo_no_postgres(engine, ids):
    if engine.dialect.name != "postgresql":
        pytest.skip("concorrencia real so no Postgres")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    _, _, a = ids
    largada = Barrier(2)

    def grava(pse):
        with Session(engine) as s:
            largada.wait()
            return svc.gravar_checkin(s, s.get(Atividade, a), svc.DadosCheckin(pse, 3, True, (), None)).pse

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(grava, [4, 5])) == [4, 5]
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(CheckinTreino)) == 1


def test_apagar_a_atividade_apaga_o_checkin(client, ids, session):
    ana, _, a = ids
    client.put(url(ana, a), json=corpo())
    session.delete(session.get(Atividade, a))
    session.commit()
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 0


def test_banco_recusa_o_que_a_api_ja_recusa(ids, session):
    """Os CHECKs valem mesmo fora da API: observacao incoerente, PSE fora da escala, texto de 501 caracteres, segundo check-in."""
    _, _, a = ids
    agora = datetime(2026, 11, 9, tzinfo=timezone.utc)

    def novo(**kw):
        base = dict(atividade_id=a, pse=5, sensacao=3, nada_a_relatar=True, versao="checkin@1", registrado_em=agora, atualizado_em=agora)
        base.update(kw)
        return CheckinTreino(**base)

    for kw in ({"pse": 11}, {"sensacao": 0}, {"dor": True}, {"texto": "x"}, {"nada_a_relatar": False}, {"nada_a_relatar": False, "texto": "x" * 501},
               {"nada_a_relatar": False, "texto": ""}):
        session.add(novo(**kw))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    session.add_all([novo(), novo()])
    with pytest.raises(IntegrityError):  # UNIQUE por atividade
        session.commit()
    session.rollback()
    session.add(novo(nada_a_relatar=False, dor=True))
    session.commit()
