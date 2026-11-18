"""`PUT /professores/{professor_id}/tipos-de-treino` (#425, ADR 0015, itens 3 e 5). Atletas e professores FICTICIOS."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.servicos.consentimento import TERMO_VIGENTE
from app.db.models import Assessoria, Atividade, Atleta, CheckinTreino, FeedbackTreino, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.main import criar_app
from tests.acesso_de_teste import sem_login
from app.servicos import professor as svc_prof
from app.servicos.feedback import desatualizado, motivos_desatualizado, tipo_atual
from app.servicos.feedback_leitura import MSG_DESATUALIZADO_TIPO, feedback_da_atividade

AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)
PROF, OUTRO = 1, 2
URL = f"/professores/{PROF}/tipos-de-treino"

# situacao -> (vinculo com PROF, consentimento, vinculo com OUTRO, aparece)
SITUACOES = {
    "consentido": (True, AGORA - timedelta(days=3), False, True),
    "consentimento_nulo": (True, None, False, False),
    "consentimento_no_futuro": (True, AGORA + timedelta(minutes=1), False, False),
    "so_de_outro_professor": (False, None, True, False),
    "sem_vinculo": (False, None, False, False),
}


@pytest.fixture
def mundo(session):
    """Um atleta por situacao, com um treino `leve` (sugestao, divergencia `sem_esforco`) e id da atividade = id do atleta."""
    session.add(Assessoria(id=1, nome="Assessoria Teste"))
    session.add_all([Professor(id=PROF, assessoria_id=1, nome="Professor Um"), Professor(id=OUTRO, assessoria_id=1, nome="Professor Dois")])
    session.flush()
    ids = {}
    for i, (nome, (vinc, cons, outro, _)) in enumerate(SITUACOES.items(), start=1):
        session.add(Atleta(id=i, assessoria_id=1, nome=f"Atleta {nome}"))
        session.flush()
        session.add(Atividade(id=i, atleta_id=i, fonte="t", fonte_id=str(i), modalidade="corrida", inicio=AGORA - timedelta(days=1),
                              duracao_s=1800, tipo_treino="leve", tipo_origem="semana_padrao", tipo_versao="tipo_treino@1",
                              tipo_divergencia="sem_esforco"))
        if vinc:
            session.add(VinculoProfessorAtleta(professor_id=PROF, atleta_id=i, consentimento_em=cons, termo_versao=TERMO_VIGENTE))
        if outro:
            session.add(VinculoProfessorAtleta(professor_id=OUTRO, atleta_id=i, consentimento_em=AGORA - timedelta(days=9), termo_versao=TERMO_VIGENTE))
        ids[nome] = i
    session.commit()
    return ids


@pytest.fixture
def client(session, mundo, monkeypatch):
    app = sem_login(criar_app("http://localhost:8081"))
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[svc_prof.agora_utc] = lambda: AGORA
    return TestClient(app, raise_server_exceptions=False)


def _a(session, i) -> Atividade:
    session.expire_all()
    return session.get(Atividade, i)


def _estado(session):
    session.expire_all()
    return [(a.id, a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia, a.tipo_confirmado, a.tipo_confirmado_por,
             a.tipo_confirmado_em) for a in session.scalars(select(Atividade).order_by(Atividade.id))]


def _tipo_404(r):
    assert r.status_code == 404
    assert r.json()["detail"][0]["type"] == "atividade_nao_encontrada"


# ---------- matriz rota x situacao ----------

@pytest.mark.parametrize("situacao", list(SITUACOES))
def test_matriz_put_por_situacao(client, session, mundo, situacao):
    aparece = SITUACOES[situacao][3]
    antes = _estado(session)
    r = client.put(URL, json=[{"atividade_id": mundo[situacao], "tipo_treino": "longo"}])
    if aparece:
        assert (r.status_code, r.json()) == (200, {"confirmados": 0, "corrigidos": 1})
        assert _a(session, mundo[situacao]).tipo_treino == "longo"
    else:
        _tipo_404(r)
        assert _estado(session) == antes  # nada gravado


def test_atividade_inexistente_e_fora_do_filtro_tem_o_mesmo_404_byte_a_byte(client, mundo):
    fora = client.put(URL, json=[{"atividade_id": mundo["consentimento_nulo"], "tipo_treino": "longo"}])
    nao_existe = client.put(URL, json=[{"atividade_id": 9999, "tipo_treino": "longo"}])
    assert fora.status_code == nao_existe.status_code == 404
    assert fora.content == nao_existe.content
    assert b"9999" not in nao_existe.content and str(mundo["consentimento_nulo"]).encode() not in fora.content.replace(b"404", b"")


def test_404_da_atividade_vem_antes_do_422_atividade_sem_tipo(client, session, mundo):
    session.get(Atividade, 1).subtipo = "multiesporte_pai"  # daria 422 sozinha
    session.commit()
    r = client.put(URL, json=[{"atividade_id": 1}, {"atividade_id": mundo["sem_vinculo"]}])
    _tipo_404(r)


# ---------- validacao de forma (422 antes do banco) ----------

@pytest.mark.parametrize("corpo", [
    [],
    [{"atividade_id": 1, "tipo_treino": "nao_existe"}],
    [{"atividade_id": 1, "tipo_treino": "LEVE"}],
    [{"atividade_id": 1, "tipo_treino": "longo"}, {"atividade_id": 1, "tipo_treino": "leve"}],
    [{"atividade_id": i} for i in range(1, 202)],
    [{"atividade_id": "x"}],
    {"atividade_id": 1},
])
def test_422_de_forma_nao_toca_no_banco_e_nao_repete_o_enviado(client, session, mundo, corpo):
    antes = _estado(session)
    r = client.put(URL, json=corpo)
    assert r.status_code == 422
    assert all(set(e) == {"loc", "msg", "type"} for e in r.json()["detail"])
    assert "nao_existe" not in r.text
    assert _estado(session) == antes


def test_lote_de_200_e_aceito(client, session, mundo):
    for k in range(10, 210):  # 200 atividades do atleta consentido
        session.add(Atividade(id=k, atleta_id=1, fonte="t", fonte_id=str(k), modalidade="corrida", inicio=AGORA - timedelta(days=2),
                              duracao_s=1800, tipo_treino="leve", tipo_origem="sugestao", tipo_versao="tipo_treino@1"))
    session.commit()
    ok = client.put(URL, json=[{"atividade_id": k} for k in range(10, 210)])
    assert ok.status_code == 200 and ok.json() == {"confirmados": 200, "corrigidos": 0}


# ---------- tudo ou nada ----------

def test_um_item_fora_do_filtro_derruba_o_lote_inteiro(client, session, mundo):
    antes = _estado(session)
    r = client.put(URL, json=[{"atividade_id": mundo["consentido"], "tipo_treino": "longo"},
                              {"atividade_id": mundo["sem_vinculo"], "tipo_treino": "longo"}])
    _tipo_404(r)
    assert _estado(session) == antes


def test_um_item_sem_tipo_derruba_o_lote_inteiro(client, session, mundo):
    sem = Atividade(id=50, atleta_id=1, fonte="t", fonte_id="50", modalidade="corrida", inicio=AGORA - timedelta(days=1), duracao_s=1800)
    session.add(sem)
    session.commit()
    antes = _estado(session)
    r = client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "longo"}, {"atividade_id": 50}])  # 50: sem tipo e sem tipo no pedido
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == "atividade_sem_tipo"
    assert "50" not in r.text
    assert _estado(session) == antes


def test_multiesporte_e_recusado_mesmo_com_tipo_no_pedido(client, session, mundo):
    session.get(Atividade, 1).subtipo = "multiesporte_pai"
    session.commit()
    r = client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "longo"}])
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == "atividade_sem_tipo"


def test_dar_tipo_a_atividade_sem_tipo_e_correcao(client, session, mundo):
    session.add(Atividade(id=50, atleta_id=1, fonte="t", fonte_id="50", modalidade="corrida", inicio=AGORA - timedelta(days=1), duracao_s=1800))
    session.commit()
    r = client.put(URL, json=[{"atividade_id": 50, "tipo_treino": "moderado"}])
    assert r.json() == {"confirmados": 0, "corrigidos": 1}
    assert _a(session, 50).tipo_origem == "professor"


# ---------- o que grava ----------

def test_corrigir_grava_origem_professor_confirmado_por_em_e_apaga_a_divergencia(client, session, mundo):
    r = client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "longo"}])
    assert r.json() == {"confirmados": 0, "corrigidos": 1}
    a = _a(session, 1)
    assert (a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia) == ("longo", "professor", None, None)
    assert a.tipo_confirmado is True and a.tipo_confirmado_por == PROF
    assert a.tipo_confirmado_em.replace(tzinfo=timezone.utc) == AGORA


@pytest.mark.parametrize("item", [{"atividade_id": 1}, {"atividade_id": 1, "tipo_treino": "leve"}])
def test_confirmar_sem_mudar_so_marca_confirmado(client, session, mundo, item):
    r = client.put(URL, json=[item])
    assert r.json() == {"confirmados": 1, "corrigidos": 0}
    a = _a(session, 1)
    assert (a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia) == ("leve", "semana_padrao", "tipo_treino@1", "sem_esforco")
    assert a.tipo_confirmado is True and a.tipo_confirmado_por == PROF and a.tipo_confirmado_em is not None


def test_repetir_a_confirmacao_nao_renova_o_tipo_confirmado_em(client, session, mundo):
    client.put(URL, json=[{"atividade_id": 1}])
    primeiro = _a(session, 1).tipo_confirmado_em
    client.app.dependency_overrides[svc_prof.agora_utc] = lambda: AGORA + timedelta(hours=5)
    r = client.put(URL, json=[{"atividade_id": 1}])
    assert r.json() == {"confirmados": 1, "corrigidos": 0}
    assert _a(session, 1).tipo_confirmado_em == primeiro


def test_resposta_conta_confirmados_e_corrigidos_juntos(client, session, mundo):
    session.add(Atividade(id=60, atleta_id=1, fonte="t", fonte_id="60", modalidade="corrida", inicio=AGORA - timedelta(days=3),
                          duracao_s=1800, tipo_treino="moderado", tipo_origem="sugestao", tipo_versao="tipo_treino@1"))
    session.commit()
    r = client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "leve"}, {"atividade_id": 60, "tipo_treino": "longo"}])
    assert r.json() == {"confirmados": 1, "corrigidos": 1}


def test_log_leva_so_ids_e_contagens(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "longo"}])
    texto = " ".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "longo" not in texto and "Atleta" not in texto


# ---------- o feedback fica desatualizado pelo tipo ----------

def _com_feedback(session, tipo_visto):
    ck = CheckinTreino(atividade_id=1, pse=5, sensacao=3, nada_a_relatar=True, dor=False, cansaco=False, sono_ruim=False, calor=False,
                       trabalho_estresse=False, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA)
    session.add(ck)
    session.flush()
    fb = FeedbackTreino(checkin_id=ck.id, estado="pronto", texto="tres linhas", versao_fatos="v", versao_prompt="p", versao_checagens="c",
                        provedor="falso", modelo="falso", tentativas=1, checkin_atualizado_em=AGORA, tipo_visto=tipo_visto, tentado_em=AGORA)
    session.add(fb)
    session.commit()
    return ck, fb


def test_correcao_deixa_o_feedback_desatualizado_pelo_motivo_tipo(client, session, mundo):
    ck, fb = _com_feedback(session, tipo_visto="leve")
    a = session.get(Atividade, 1)
    assert not desatualizado(fb, ck, "v", tipo_hoje=tipo_atual(a))
    client.put(URL, json=[{"atividade_id": 1, "tipo_treino": "longo"}])
    session.expire_all()
    a, fb, ck = session.get(Atividade, 1), session.get(FeedbackTreino, fb.id), session.get(CheckinTreino, ck.id)
    assert motivos_desatualizado(fb, ck, "v", tipo_hoje=tipo_atual(a)) == {"tipo"}
    lido = feedback_da_atividade(a, ck, False, versao_fatos="v", tipo_hoje=tipo_atual(a))
    assert (lido.estado, lido.mensagem) == ("desatualizado", MSG_DESATUALIZADO_TIPO)


def test_confirmar_sem_mudar_nao_desatualiza_o_feedback(client, session, mundo):
    ck, fb = _com_feedback(session, tipo_visto="leve")
    client.put(URL, json=[{"atividade_id": 1}])
    session.expire_all()
    assert not desatualizado(session.get(FeedbackTreino, fb.id), session.get(CheckinTreino, ck.id), "v", tipo_hoje=tipo_atual(session.get(Atividade, 1)))


def test_tipo_visto_nulo_nao_compara_e_sem_tipo_e_um_valor(session, mundo):
    ck, fb = _com_feedback(session, tipo_visto=None)
    assert not desatualizado(fb, ck, "v", tipo_hoje="longo")
    fb.tipo_visto = "sem_tipo"
    assert motivos_desatualizado(fb, ck, "v", tipo_hoje="leve") == {"tipo"}
    assert not motivos_desatualizado(fb, ck, "v")  # sem `tipo_hoje`, o tipo nao entra na conta
