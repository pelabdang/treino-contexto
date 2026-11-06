"""Comando `worker.reclassificar_multiesporte` (issue #230). Dado sintetico; sem rede."""

import os
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta
from app.ingestao.importacao import importar
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worker.reclassificar_multiesporte import imprimir, main, reclassificar_multiesporte

EXPORTACAO = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "multiesporte" / "exportacao_multiesporte.json"
PAI, TROCA1, TROCA2, NATACAO = "3000000201", "3000000203", "3000000205", "3000000202"


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


def _ativ(session, fonte_id):
    return session.query(Atividade).filter_by(fonte_id=fonte_id).one()


@pytest.fixture
def importado_antigo(session):
    """Importa e simula o banco anterior ao #230: pai e trocas `outra` sem subtipo."""
    importar(session, EXPORTACAO, "Atleta Ficticio")
    session.query(Atividade).filter(Atividade.modalidade == "outra").update({"subtipo": None})
    session.commit()
    return session


def test_marca_pai_e_trocas(importado_antigo):
    s = importado_antigo
    rel = reclassificar_multiesporte(s, EXPORTACAO)
    assert rel.mudancas == {(None, "multiesporte_pai"): 1, (None, "troca"): 2}
    assert rel.gravou and rel.fora_da_exportacao == 0
    s.expire_all()
    assert _ativ(s, PAI).subtipo == "multiesporte_pai"
    assert _ativ(s, TROCA1).subtipo == _ativ(s, TROCA2).subtipo == "troca"
    assert _ativ(s, PAI).modalidade == "outra"


def test_segunda_rodada_muda_zero(importado_antigo):
    reclassificar_multiesporte(importado_antigo, EXPORTACAO)
    assert reclassificar_multiesporte(importado_antigo, EXPORTACAO).total == 0


def test_dry_run_nao_grava(importado_antigo):
    s = importado_antigo
    rel = reclassificar_multiesporte(s, EXPORTACAO, dry_run=True)
    assert rel.total == 3 and not rel.gravou
    s.expire_all()
    assert _ativ(s, PAI).subtipo is None


def test_so_mexe_no_subtipo_de_outra(importado_antigo):
    s = importado_antigo
    _ativ(s, PAI).subtipo = "esteira"  # subtipo de outro tipo nao e sobrescrito
    _ativ(s, NATACAO).subtipo = None
    s.commit()
    antes = {a.id: (a.modalidade, a.inicio, a.duracao_s, a.distancia_m, a.fc_media) for a in s.query(Atividade)}
    rel = reclassificar_multiesporte(s, EXPORTACAO)
    assert rel.mudancas == {(None, "troca"): 2}
    s.expire_all()
    assert _ativ(s, PAI).subtipo == "esteira" and _ativ(s, NATACAO).subtipo is None
    assert {a.id: (a.modalidade, a.inicio, a.duracao_s, a.distancia_m, a.fc_media) for a in s.query(Atividade)} == antes


def test_conta_fora_da_exportacao_e_filtra_atleta(importado_antigo):
    s = importado_antigo
    outro = Atleta(nome="Outro")
    s.add(outro)
    s.flush()
    s.add(Atividade(atleta_id=outro.id, fonte="garmin_export", fonte_id="999", modalidade="outra",
                    inicio=_ativ(s, PAI).inicio, duracao_s=60.0))
    s.commit()
    rel = reclassificar_multiesporte(s, EXPORTACAO, atleta_id=outro.id)
    assert rel.total == 0 and rel.fora_da_exportacao == 1


def test_imprime_e_main(importado_antigo, monkeypatch, capsys):
    imprimir(reclassificar_multiesporte(importado_antigo, EXPORTACAO, dry_run=True), True)
    out = capsys.readouterr().out
    assert "NULL -> multiesporte_pai: 1" in out and "NULL -> troca: 2" in out and "dry-run" in out
    import app.db.session as sessao
    monkeypatch.setattr(sessao, "SessionLocal", lambda: importado_antigo)
    assert main(["--exportacao", str(EXPORTACAO), "--dry-run"]) == 0
