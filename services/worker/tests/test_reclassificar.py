"""Comando `worker.reclassificar` (issue #64), com as fixtures importadas no banco."""

import os
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, Segmento
from app.metricas.tiros_1km import VERSAO
from app.servicos.evolucao_tiros import reclassificacao_pendente
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import worker.reclassificar as cmd
from worker.importar_garmin import importar
from worker.reclassificar import AtletaInexistente, reclassificar

ZIP = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"


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
    importar(session, ZIP, "Atleta Ficticio")
    return session.query(Atleta).one()


def _envelhecer(session):
    for s in session.query(Segmento):
        s.versao_deteccao = "tiros_1km@1"
    session.commit()


def test_reclassifica_e_limpa_o_pendente(session, atleta):
    assert not reclassificacao_pendente(session, atleta.id)
    _envelhecer(session)
    assert reclassificacao_pendente(session, atleta.id)
    n = reclassificar(session, atleta.id)
    assert n == 4  # as 4 corridas das fixtures (a quinta atividade não é corrida)
    assert not reclassificacao_pendente(session, atleta.id)
    corridas = session.query(Segmento).join(Segmento.atividade).filter(Atividade.modalidade == "corrida")
    assert {s.versao_deteccao for s in corridas} == {VERSAO}


def test_bloco_com_versao_velha_de_esforcos_tambem_pede_reclassificar(session, atleta):
    # #168: a série lê bloco_atividade; bloco gravado por outra versão dos esforços também deixa a série pendente.
    from app.db.models import BlocoAtividade

    assert session.query(BlocoAtividade).count() > 0
    for b in session.query(BlocoAtividade):
        b.versao_deteccao = "esforcos@0"
    session.commit()
    assert reclassificacao_pendente(session, atleta.id)
    reclassificar(session, atleta.id)
    assert not reclassificacao_pendente(session, atleta.id)
    assert {b.versao_deteccao for b in session.query(BlocoAtividade)} == {"esforcos@1"}


def test_idempotente(session, atleta):
    antes = sorted((s.id, s.tipo, s.versao_deteccao) for s in session.query(Segmento))
    assert reclassificar(session, atleta.id) == reclassificar(session, atleta.id)
    assert sorted((s.id, s.tipo, s.versao_deteccao) for s in session.query(Segmento)) == antes


def test_atleta_inexistente(session):
    with pytest.raises(AtletaInexistente):
        reclassificar(session, 9999)


def test_cli(engine, atleta, session, capsys, monkeypatch):
    import app.db.session as sess
    monkeypatch.setattr(sess, "SessionLocal", lambda: Session(engine))
    _envelhecer(session)
    assert cmd.main(["--atleta-id", str(atleta.id)]) == 0
    assert capsys.readouterr().out.strip() == f"reclassificadas 4 corridas do atleta {atleta.id}"
    assert cmd.main(["--atleta-id", "9999"]) == 1
    assert "não encontrado" in capsys.readouterr().err


def test_reclassificar_regrava_o_tipo_antigo_e_limpa_o_pendente(session, atleta):
    """Sugestao gravada antes da 0011 (sem `tipo_versao`) fica pendente; o comando a regrava com `tipo_treino@1`."""
    reclassificar(session, atleta.id)
    sugeridas = session.query(Atividade).filter(Atividade.tipo_origem == "sugestao").all()
    assert sugeridas and all(a.tipo_versao == "tipo_treino@1" for a in sugeridas)
    for a in sugeridas:
        a.tipo_versao = None
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is True
    reclassificar(session, atleta.id)
    session.expire_all()
    assert reclassificacao_pendente(session, atleta.id) is False
    assert all(a.tipo_versao == "tipo_treino@1" for a in session.query(Atividade).filter(Atividade.tipo_origem == "sugestao"))
