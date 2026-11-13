"""Camada de banco da recuperacao diaria (ADR 0014, itens 1 e 5; #372). Dados sinteticos."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino, RecuperacaoDia
from app.servicos import recuperacao_banco as rb

T0 = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=5)
V = "recuperacao_leitura@1"


def _atleta(session, nome="Ana"):
    a = Atleta(nome=nome)
    session.add(a)
    session.flush()
    return a.id


def _n(session, atleta_id):
    return session.scalar(select(func.count()).select_from(RecuperacaoDia).where(RecuperacaoDia.atleta_id == atleta_id))


def test_upsert_nova_igual_e_atualizada(session):
    a = _atleta(session)
    d = date(2026, 3, 10)
    assert rb.gravar_noite(session, a, d, 22500, 128.0, 54, V, T0) == "nova"
    assert rb.gravar_noite(session, a, d, 22500, 128.0, 54, V, T1) == "igual"
    linha = rb.noites_do_atleta(session, a)[d]
    assert linha.importado_em.replace(tzinfo=None) == T0.replace(tzinfo=None)  # igual: nao muda
    assert rb.gravar_noite(session, a, d, 23000, 128.0, 54, "recuperacao_leitura@2", T1) == "atualizada"
    linha = session.scalars(select(RecuperacaoDia)).one()
    assert linha.sono_s == 23000 and linha.importado_em.replace(tzinfo=None) == T1.replace(tzinfo=None)
    assert linha.versao_leitura == "recuperacao_leitura@2" and _n(session, a) == 1


def test_valor_nulo_nunca_apaga_o_que_ja_esta_guardado(session):
    a = _atleta(session)
    d = date(2026, 3, 10)
    rb.gravar_noite(session, a, d, 22500, 128.0, 54, V, T0)
    assert rb.gravar_noite(session, a, d, None, None, None, V, T1) == "igual"
    assert rb.gravar_noite(session, a, d, None, 130.0, None, V, T1) == "atualizada"  # so a VFC muda
    linha = session.scalars(select(RecuperacaoDia)).one()
    assert (linha.sono_s, linha.vfc_ms, linha.fc_repouso_bpm) == (22500, 130.0, 54)


def test_noite_sem_nenhuma_medida_nao_vira_linha(session):
    a = _atleta(session)
    assert rb.gravar_noite(session, a, date(2026, 3, 10), None, None, None, V, T0) is None
    assert _n(session, a) == 0
    assert rb.gravar_noite(session, a, date(2026, 3, 10), None, None, 52, V, T0) == "nova"  # so uma medida basta


def test_leitura_em_lote_por_faixa_e_por_atleta(session):
    a, b = _atleta(session), _atleta(session, "Beto")
    for i in range(5):
        rb.gravar_noite(session, a, date(2026, 3, 10) + timedelta(days=i), 20000 + i, None, None, V, T0)
    rb.gravar_noite(session, b, date(2026, 3, 10), 1, None, None, V, T0)
    todas = rb.noites_do_atleta(session, a)
    assert list(todas) == [date(2026, 3, 10) + timedelta(days=i) for i in range(5)]  # em ordem, uma chave por data
    janela = rb.noites_do_atleta(session, a, desde=date(2026, 3, 11), ate=date(2026, 3, 13))
    assert [n.sono_s for n in janela.values()] == [20001, 20002, 20003]
    assert date(2026, 3, 20) not in todas  # ausencia da chave = sem dado
    assert rb.primeira_noite(session, a) == date(2026, 3, 10) and rb.ultima_noite(session, a) == date(2026, 3, 14)
    assert rb.primeira_noite(session, _atleta(session, "Caio")) is None


def _feedback(session, atleta_id, fonte_id, recuperacao):
    at = Atividade(atleta_id=atleta_id, fonte="t", fonte_id=fonte_id, modalidade="corrida", inicio=T0, duracao_s=1800.0)
    session.add(at)
    session.flush()
    c = CheckinTreino(atividade_id=at.id, pse=5, sensacao=3, nada_a_relatar=True, versao="checkin@1",
                      registrado_em=T0, atualizado_em=T0)
    session.add(c)
    session.flush()
    session.add(FeedbackTreino(checkin_id=c.id, estado="pronto", texto="Texto sintetico.", versao_fatos="fatos_treino@2",
                               versao_prompt="p", versao_checagens="c", provedor="falso", modelo="falso",
                               checkin_atualizado_em=T0, tentado_em=T0, recuperacao_importada_em=recuperacao))
    session.flush()


def test_apagar_so_as_noites_e_os_feedbacks_que_usaram_a_recuperacao(session):
    a, b = _atleta(session), _atleta(session, "Beto")
    for atl in (a, b):
        rb.gravar_noite(session, atl, date(2026, 3, 10), 20000, None, None, V, T0)
    _feedback(session, a, "1", T0)
    _feedback(session, a, "2", None)
    _feedback(session, b, "3", T0)
    session.commit()
    assert rb.apagar_recuperacao_do_atleta(session, a) == (1, 1)
    assert _n(session, a) == 0 and _n(session, b) == 1  # outro atleta intacto
    restantes = session.scalars(select(FeedbackTreino).order_by(FeedbackTreino.id)).all()
    assert [f.recuperacao_importada_em is None for f in restantes] == [True, False]  # o sem recuperacao fica; o do outro fica
    assert session.scalar(select(func.count()).select_from(CheckinTreino)) == 3  # check-ins e atividades ficam
    assert session.scalar(select(func.count()).select_from(Atividade)) == 3
    assert rb.apagar_recuperacao_do_atleta(session, a) == (0, 0)  # idempotente
