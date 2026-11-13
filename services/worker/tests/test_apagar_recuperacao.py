"""Comando `worker.apagar_recuperacao` (issue #372, ADR 0014 item 5). Dados sinteticos."""

import logging
import os
from datetime import date, datetime, timezone

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino, RecuperacaoDia
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker import apagar_recuperacao

AGORA = datetime(2026, 3, 16, tzinfo=timezone.utc)
MARCADOR = "MARCADOR-SINTETICO-META10-NAO-LOGAR"


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def fabrica(engine, monkeypatch):
    from app.db import session as sessao

    f = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(sessao, "SessionLocal", f)
    return f


def _popular(fabrica):
    """Ana e Beto: 3 noites e 2 feedbacks cada um (um com a recuperacao, um sem)."""
    with fabrica() as s:
        for nome in ("Ana", "Beto"):
            at = Atleta(nome=nome)
            s.add(at)
            s.flush()
            for i in range(3):
                s.add(RecuperacaoDia(atleta_id=at.id, origem="garmin_connect", noite=date(2026, 3, 10 + i), sono_s=20000,
                                     versao_leitura="recuperacao_leitura@1", importado_em=AGORA))
            for i, rec in enumerate((AGORA, None)):
                a = Atividade(atleta_id=at.id, fonte="t", fonte_id=str(i), modalidade="corrida", inicio=AGORA, duracao_s=1800.0)
                s.add(a)
                s.flush()
                c = CheckinTreino(atividade_id=a.id, pse=5, sensacao=3, nada_a_relatar=True, versao="checkin@1",
                                  registrado_em=AGORA, atualizado_em=AGORA)
                s.add(c)
                s.flush()
                s.add(FeedbackTreino(checkin_id=c.id, estado="pronto", texto=MARCADOR, versao_fatos="fatos_treino@2",
                                     versao_prompt="p", versao_checagens="c", provedor="f", modelo="f",
                                     checkin_atualizado_em=AGORA, tentado_em=AGORA, recuperacao_importada_em=rec))
        s.commit()


def _contagens(fabrica, nome):
    with fabrica() as s:
        at = s.scalars(select(Atleta).where(Atleta.nome == nome)).one()
        return (s.scalar(select(func.count()).select_from(RecuperacaoDia).where(RecuperacaoDia.atleta_id == at.id)),
                s.scalar(select(func.count()).select_from(FeedbackTreino).join(CheckinTreino).join(Atividade)
                         .where(Atividade.atleta_id == at.id)),
                s.scalar(select(func.count()).select_from(CheckinTreino).join(Atividade).where(Atividade.atleta_id == at.id)),
                s.scalar(select(func.count()).select_from(Atividade).where(Atividade.atleta_id == at.id)))


def test_apaga_as_noites_e_so_os_feedbacks_que_usaram_a_recuperacao(fabrica, capsys, caplog):
    _popular(fabrica)
    with caplog.at_level(logging.DEBUG):
        assert apagar_recuperacao.main(["--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert saida.out.splitlines() == ["recuperacao: apagadas=3", "feedbacks: apagados=1"]
    assert MARCADOR not in saida.out + saida.err + caplog.text
    assert _contagens(fabrica, "Ana") == (0, 1, 2, 2)  # o feedback sem recuperacao, os check-ins e as atividades ficam
    assert _contagens(fabrica, "Beto") == (3, 2, 2, 2)  # o outro atleta nao muda


def test_idempotente(fabrica, capsys):
    _popular(fabrica)
    apagar_recuperacao.main(["--atleta", "Ana"])
    capsys.readouterr()
    assert apagar_recuperacao.main(["--atleta", "Ana"]) == 0
    assert capsys.readouterr().out.splitlines() == ["recuperacao: apagadas=0", "feedbacks: apagados=0"]


def test_atleta_inexistente_sai_com_1(fabrica, capsys):
    _popular(fabrica)
    assert apagar_recuperacao.main(["--atleta", "Ninguem"]) == 1
    assert "nao encontrado" in capsys.readouterr().err
    assert _contagens(fabrica, "Ana")[0] == 3


def test_nome_repetido_apaga_so_o_de_menor_id(fabrica, capsys):
    with fabrica() as s:
        ids = []
        for _ in range(2):
            at = Atleta(nome="Igual")
            s.add(at)
            s.flush()
            ids.append(at.id)
            s.add(RecuperacaoDia(atleta_id=at.id, origem="garmin_connect", noite=date(2026, 3, 10), sono_s=1,
                                 versao_leitura="v", importado_em=AGORA))
        s.commit()
    assert apagar_recuperacao.main(["--atleta", "Igual"]) == 0
    assert "2 atletas" in capsys.readouterr().err
    with fabrica() as s:
        assert [r.atleta_id for r in s.scalars(select(RecuperacaoDia))] == [ids[1]]
