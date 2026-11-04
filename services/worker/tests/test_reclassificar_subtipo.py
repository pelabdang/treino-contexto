"""Comando `worker.reclassificar_subtipo` (issue #183). Dado sintetico das fixtures de clima; sem rede."""

import os
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta
from app.ingestao.importacao import importar
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worker.reclassificar_subtipo import imprimir, main, reclassificar_subtipo

EXPORTACAO = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "clima" / "exportacao_clima.json"
VIRTUAL, ESTEIRA, CORRIDA = "3000000104", "3000000102", "3000000101"


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
    """Importa e depois simula o mapeamento antigo: virtual e esteira sem subtipo, virtual com posicao."""
    importar(session, EXPORTACAO, "Atleta Ficticio")
    virtual = _ativ(session, VIRTUAL)
    virtual.subtipo, virtual.inicio_lat, virtual.inicio_lon = None, 12.35, -45.68
    _ativ(session, ESTEIRA).subtipo = None
    session.commit()
    return session


def test_virtual_ride_sem_subtipo_vira_virtual(importado_antigo):
    s = importado_antigo
    rel = reclassificar_subtipo(s, EXPORTACAO)
    assert rel.mudancas == {(None, "virtual"): 1, (None, "esteira"): 1}
    assert rel.gravou
    s.expire_all()
    assert _ativ(s, VIRTUAL).subtipo == "virtual"
    assert _ativ(s, ESTEIRA).subtipo == "esteira"


def test_virar_indoor_apaga_a_posicao(importado_antigo):
    s = importado_antigo
    rel = reclassificar_subtipo(s, EXPORTACAO)
    assert rel.sem_posicao_apagada == 1
    s.expire_all()
    assert _ativ(s, VIRTUAL).inicio_lat is None and _ativ(s, VIRTUAL).inicio_lon is None


def test_segunda_rodada_muda_zero(importado_antigo):
    reclassificar_subtipo(importado_antigo, EXPORTACAO)
    rel = reclassificar_subtipo(importado_antigo, EXPORTACAO)
    assert rel.total == 0 and rel.sem_posicao_apagada == 0


def test_dry_run_nao_grava(importado_antigo):
    s = importado_antigo
    rel = reclassificar_subtipo(s, EXPORTACAO, dry_run=True)
    assert rel.total == 2 and not rel.gravou
    s.expire_all()
    assert _ativ(s, VIRTUAL).subtipo is None and _ativ(s, ESTEIRA).subtipo is None
    assert _ativ(s, VIRTUAL).inicio_lat == 12.35  # posicao intacta no dry-run


def test_so_mexe_no_subtipo(importado_antigo):
    s = importado_antigo
    antes = {a.id: (a.modalidade, a.inicio, a.duracao_s, a.distancia_m, a.fc_media, a.arquivo_bruto, a.fuso_min,
                    a.tipo_treino, len(a.segmentos)) for a in s.query(Atividade)}
    reclassificar_subtipo(s, EXPORTACAO)
    s.expire_all()
    depois = {a.id: (a.modalidade, a.inicio, a.duracao_s, a.distancia_m, a.fc_media, a.arquivo_bruto, a.fuso_min,
                     a.tipo_treino, len(a.segmentos)) for a in s.query(Atividade)}
    assert depois == antes


def test_diverge_e_corrigido_mas_none_da_exportacao_nao_apaga(importado_antigo):
    s = importado_antigo
    _ativ(s, ESTEIRA).subtipo = "pista"  # divergente
    _ativ(s, CORRIDA).subtipo = "trilha"  # a exportacao diz None (running sem detalhe): nao apaga
    s.commit()
    rel = reclassificar_subtipo(s, EXPORTACAO)
    assert rel.mudancas[("pista", "esteira")] == 1
    s.expire_all()
    assert _ativ(s, CORRIDA).subtipo == "trilha"


def test_filtra_por_atleta_e_conta_o_que_a_exportacao_nao_traz(importado_antigo):
    s = importado_antigo
    outro = Atleta(nome="Outro")
    s.add(outro)
    s.flush()
    s.add(Atividade(atleta_id=outro.id, fonte="garmin_export", fonte_id="999", modalidade="ciclismo",
                    inicio=_ativ(s, CORRIDA).inicio, duracao_s=60.0))
    s.commit()
    rel = reclassificar_subtipo(s, EXPORTACAO, atleta_id=outro.id)
    assert rel.total == 0 and rel.fora_da_exportacao == 1
    s.expire_all()
    assert _ativ(s, VIRTUAL).subtipo is None


def test_imprime_contagens(importado_antigo, capsys):
    imprimir(reclassificar_subtipo(importado_antigo, EXPORTACAO, dry_run=True), True)
    out = capsys.readouterr().out
    assert "NULL -> virtual: 1" in out and "dry-run" in out


def test_main_usa_session_local(importado_antigo, monkeypatch, capsys):
    import app.db.session as sessao
    monkeypatch.setattr(sessao, "SessionLocal", lambda: importado_antigo)
    assert main(["--exportacao", str(EXPORTACAO), "--dry-run"]) == 0
    assert "NULL -> virtual: 1" in capsys.readouterr().out
