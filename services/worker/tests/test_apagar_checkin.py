"""Comando `worker.apagar_checkin` (issue #296, ADR 0012 item 5) e a reimportacao que preserva o check-in. Dados sinteticos."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CheckinTreino
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker import apagar_checkin
from worker.importar_garmin import importar

ZIP = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
MARCADOR = "MARCADOR-SINTETICO-123"
AGORA = datetime(2026, 11, 9, tzinfo=timezone.utc)


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


def _checkin(session, atividade_id):
    session.add(CheckinTreino(atividade_id=atividade_id, pse=6, sensacao=3, nada_a_relatar=False, dor=True, texto=MARCADOR,
                              versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA))


def _dois_atletas(fabrica):
    with fabrica() as s:
        for nome in ("Ana", "Beto"):
            at = Atleta(nome=nome)
            s.add(at)
            s.flush()
            for i in range(2):
                a = Atividade(atleta_id=at.id, fonte="t", fonte_id=str(i), modalidade="corrida", inicio=AGORA, duracao_s=1800.0)
                s.add(a)
                s.flush()
                _checkin(s, a.id)
        s.commit()


def _conta(fabrica, modelo=CheckinTreino):
    with fabrica() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def test_apaga_so_os_checkins_do_atleta_escolhido_e_a_segunda_rodada_nao_faz_nada(fabrica, capsys, caplog):
    _dois_atletas(fabrica)
    caplog.set_level(logging.DEBUG)
    assert apagar_checkin.main(["--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert saida.out == "checkins: apagados=2\n" and MARCADOR not in saida.out + saida.err + caplog.text
    assert _conta(fabrica) == 2  # os do Beto ficam
    with fabrica() as s:
        assert {a.atleta.nome for a in s.scalars(select(Atividade)) if a.checkin is not None} == {"Beto"}
    assert _conta(fabrica, Atividade) == 4 and _conta(fabrica, Atleta) == 2  # atividades e atletas ficam
    assert apagar_checkin.main(["--atleta", "Ana"]) == 0
    assert capsys.readouterr().out == "checkins: apagados=0\n"
    assert _conta(fabrica) == 2


def test_atleta_inexistente(fabrica, capsys):
    assert apagar_checkin.main(["--atleta", "Ninguem"]) == 1
    assert "erro" in capsys.readouterr().err


def test_nome_repetido_apaga_so_o_de_menor_id_e_avisa(fabrica, capsys):
    with fabrica() as s:
        ids = []
        for _ in range(2):
            at = Atleta(nome="Igual")
            s.add(at)
            s.flush()
            a = Atividade(atleta_id=at.id, fonte="t", fonte_id="1", modalidade="corrida", inicio=AGORA, duracao_s=1800.0)
            s.add(a)
            s.flush()
            _checkin(s, a.id)
            ids.append(at.id)
        s.commit()
    assert apagar_checkin.main(["--atleta", "Igual"]) == 0
    cap = capsys.readouterr()
    assert cap.out == "checkins: apagados=1\n" and "outros ficam" in cap.err
    with fabrica() as s:
        restante = s.scalars(select(CheckinTreino)).one()
        assert restante.atividade.atleta_id == max(ids)


def test_reimportar_mantem_o_checkin(fabrica):
    """A importacao atualiza a atividade no lugar (mesma chave da fonte): recriar apagaria o check-in pela cascata."""
    with fabrica() as s:
        importar(s, ZIP, "Atleta Ficticio")
        alvo = s.scalars(select(Atividade).order_by(Atividade.id)).first()
        _checkin(s, alvo.id)
        s.commit()
        alvo_id, total = alvo.id, _conta(fabrica, Atividade)
    with fabrica() as s:
        importar(s, ZIP, "Atleta Ficticio")
    assert _conta(fabrica, Atividade) == total
    with fabrica() as s:
        assert s.scalars(select(CheckinTreino)).one().atividade_id == alvo_id
