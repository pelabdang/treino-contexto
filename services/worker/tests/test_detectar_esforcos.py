"""Comando `worker.detectar_esforcos` (issue #166), com as fixtures sintéticas da #161 e a exportação mínima."""

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, BlocoAtividade
from app.ingestao.garmin import ler_atividade_fit
from app.ingestao.importacao import duracao_da, gravar_atividade
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import worker.detectar_esforcos as cmd
from worker.detectar_esforcos import AtletaInexistente, detectar
from worker.importar_garmin import importar

RAIZ = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "garmin"
ZIP = RAIZ / "exportacao_minima.zip"
FIT = RAIZ / "esforcos" / "esforcos_corrida_1500_lap_automatico.fit"


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    session.add(Atividade(  # histórico: ritmo habitual de 330 s/km (referência do oráculo da #161)
        atleta_id=a.id, fonte="teste", fonte_id="hist", modalidade="corrida",
        inicio=datetime(2020, 1, 1, 8, tzinfo=timezone.utc), duracao_s=1650.0, distancia_m=5000.0,
    ))
    ler = ler_atividade_fit(FIT.read_bytes(), fonte="fit_upload")
    gravar_atividade(session, a.id, ler, duracao_da(ler), [])
    session.commit()
    return a


def _n_blocos(session):
    return session.scalar(select(func.count()).select_from(BlocoAtividade))


def test_detecta_e_a_segunda_rodada_nao_muda(session, atleta):
    rel = detectar(session, atleta.id)
    assert (rel.processadas, rel.alteradas) == (2, 1) and _n_blocos(session) == 5
    ids = sorted(session.scalars(select(BlocoAtividade.id)))
    rel = detectar(session, atleta.id)
    assert (rel.alteradas, rel.inalteradas) == (0, 2)
    assert sorted(session.scalars(select(BlocoAtividade.id))) == ids


def test_importar_ja_grava_os_blocos(session):
    importar(session, ZIP, "Atleta Ficticio")
    assert _n_blocos(session) > 0  # as corridas das fixtures ganharam blocos na própria importação
    atleta = session.query(Atleta).one()
    assert detectar(session, atleta.id).alteradas == 0  # e o comando não tem mais nada a mudar


def test_atleta_inexistente(session):
    with pytest.raises(AtletaInexistente):
        detectar(session, 9999)


def test_cli(engine, atleta, capsys, monkeypatch):
    import app.db.session as sess

    monkeypatch.setattr(sess, "SessionLocal", lambda: Session(engine))
    assert cmd.main(["--atleta-id", str(atleta.id)]) == 0
    saida = capsys.readouterr().out
    assert "esforcos esforcos@1" in saida
    assert "atividades processadas: 2 (gravadas de novo: 1, sem mudança: 1, sem blocos: 1)" in saida
    assert "corrida: esforcos=3 treinos-chave=0" in saida
    assert "corrida d1500=3" in saida
    assert cmd.main(["--atleta-id", str(atleta.id)]) == 0
    assert "gravadas de novo: 0, sem mudança: 2" in capsys.readouterr().out
    assert cmd.main(["--atleta-id", "9999"]) == 1
    assert "não encontrado" in capsys.readouterr().err
