"""Importacao da exportacao Garmin no banco (issue #13)."""

import os
import shutil
import zipfile
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, Segmento
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from worker.importar_garmin import importar, main, normalizar_intensidade, pace_s_km

RAIZ = Path(__file__).resolve().parents[3]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
TOTAL_VOLTAS = 13 + 11 + 8 + 4  # fixtures A, B, C, D (E nao tem FIT)


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


def _conta(session, modelo):
    return session.scalar(select(func.count()).select_from(modelo))


def test_banco_vazio(session):
    rel = importar(session, ZIP, "Atleta Ficticio")
    assert (rel.inseridas, rel.atualizadas, rel.ignoradas) == (5, 0, 0)
    assert _conta(session, Atleta) == 1 and _conta(session, Atividade) == 5
    assert _conta(session, Segmento) == TOTAL_VOLTAS
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    assert ativ.fonte == "garmin_export" and ativ.modalidade == "corrida" and len(ativ.segmentos) == 13
    assert sum(s.distancia_m for s in ativ.segmentos) == 11500
    assert sum(s.duracao_s for s in ativ.segmentos) == 3560
    primeiro_tiro = ativ.segmentos[1]
    assert (primeiro_tiro.tipo, primeiro_tiro.intensidade, primeiro_tiro.duracao_s) == ("tiro", "active", 255)
    assert primeiro_tiro.pace_s_km == 255.0 and primeiro_tiro.fc_media == 165
    assert primeiro_tiro.versao_deteccao == "tiros_1km@1"  # a importacao classifica no fim (#14)
    assert (ativ.tipo_treino, ativ.tipo_origem) == ("intervalado", "sugestao")
    esteira = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000005")).one()
    assert esteira.subtipo == "esteira" and esteira.segmentos == []


def test_reimportar_nao_duplica(session):
    importar(session, ZIP, "Atleta Ficticio")
    ids = {a.fonte_id: a.id for a in session.scalars(select(Atividade))}
    seg_ids = set(session.scalars(select(Segmento.id)))
    rel = importar(session, ZIP, "Atleta Ficticio")
    assert (rel.inseridas, rel.atualizadas, rel.ignoradas) == (0, 0, 5)
    assert _conta(session, Atleta) == 1 and _conta(session, Atividade) == 5
    assert _conta(session, Segmento) == TOTAL_VOLTAS
    assert {a.fonte_id: a.id for a in session.scalars(select(Atividade))} == ids
    assert set(session.scalars(select(Segmento.id))) == seg_ids  # nem os segmentos foram recriados


def _recortar(tmp_path, manter_ids):
    """Copia a exportacao deixando so algumas atividades no JSON (os FITs ficam todos)."""
    import json
    destino = tmp_path / "parcial"
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(destino)
    arq = next(destino.rglob("*summarizedActivities.json"))
    dados = json.loads(arq.read_text())
    dados[0]["summarizedActivitiesExport"] = [
        i for i in dados[0]["summarizedActivitiesExport"] if str(i["activityId"]) in manter_ids]
    arq.write_text(json.dumps(dados))
    return destino


def test_importacao_parcial_depois_completa(session, tmp_path):
    parcial = _recortar(tmp_path, {"1000000001", "1000000002", "1000000005"})
    # o FIT das atividades fora do JSON entraria como atividade propria: remove o zip interno e deixa so 2 FITs
    interno = next(parcial.rglob("UploadedFiles_0-_Part1.zip"))
    with zipfile.ZipFile(interno) as z:
        z.extractall(interno.parent)
    interno.unlink()
    for f in interno.parent.glob("*.fit"):
        if not f.name.endswith(("1000000001.fit", "1000000002.fit")):
            f.unlink()
    rel = importar(session, parcial, "Atleta Ficticio")
    assert rel.inseridas == 3 and _conta(session, Atividade) == 3
    rel = importar(session, ZIP, "Atleta Ficticio")
    assert (rel.inseridas, rel.ignoradas) == (2, 3)
    assert _conta(session, Atividade) == 5 and _conta(session, Segmento) == TOTAL_VOLTAS


def test_atleta_existente_e_reutilizado_e_outro_nome_cria_outro(session):
    importar(session, ZIP, "Ana")
    importar(session, ZIP, "Ana")
    assert _conta(session, Atleta) == 1
    importar(session, ZIP, "Beto")
    assert _conta(session, Atleta) == 2 and _conta(session, Atividade) == 10


def test_atualiza_atividade_e_substitui_segmentos_mantendo_id(session):
    importar(session, ZIP, "Ana")
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    id_original = ativ.id
    ativ.fc_media = 100  # banco diverge da fonte
    ativ.segmentos[0].duracao_s = 1
    session.commit()
    rel = importar(session, ZIP, "Ana")
    assert (rel.atualizadas, rel.ignoradas, rel.inseridas) == (1, 4, 0)
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    assert ativ.id == id_original and ativ.fc_media == 153
    assert len(ativ.segmentos) == 13 and ativ.segmentos[0].duracao_s == 720
    assert _conta(session, Segmento) == TOTAL_VOLTAS


def test_reimportar_sem_voltas_nao_apaga_as_gravadas(session, tmp_path):
    importar(session, ZIP, "Ana")
    json_so = _recortar(tmp_path, {"1000000001"})
    interno = next(json_so.rglob("UploadedFiles_0-_Part1.zip"))
    interno.unlink()  # sem FIT: so o JSON
    rel = importar(session, json_so, "Ana")
    assert _conta(session, Segmento) == TOTAL_VOLTAS
    assert any("mantidas as 13" in a for a in rel.avisos)


def test_avisos_do_parser_no_relatorio(session):
    rel = importar(session, ZIP, "Ana")
    assert any("1000000005 sem FIT" in a for a in rel.avisos)


def test_intensidade_normalizada():
    assert normalizar_intensidade("Active") == "active"
    assert normalizar_intensidade("  REST ") == "rest"
    assert normalizar_intensidade("cooldown") == "cooldown"
    assert normalizar_intensidade("sprint") == "other"  # fora da lista: other, nao erro
    assert normalizar_intensidade("") == "other"
    assert normalizar_intensidade(None) is None


def test_intensidade_estranha_vai_para_other_sem_erro(session, monkeypatch):
    from worker import importar_garmin
    from worker.garmin import ler_exportacao
    originais = ler_exportacao(ZIP)
    originais[0].voltas[1] = originais[0].voltas[1].__class__(
        **{**originais[0].voltas[1].__dict__, "intensidade": " Active "})
    originais[0].voltas[2] = originais[0].voltas[2].__class__(
        **{**originais[0].voltas[2].__dict__, "intensidade": "Sprint"})
    monkeypatch.setattr(importar_garmin, "ler_exportacao", lambda _: originais)
    importar(session, ZIP, "Ana")  # nao levanta IntegrityError no CHECK
    segs = session.scalars(select(Segmento).join(Atividade).where(Atividade.fonte_id == originais[0].fonte_id)
                           .order_by(Segmento.ordem)).all()
    assert segs[1].intensidade == "active" and segs[2].intensidade == "other"


def test_pace():
    assert pace_s_km(255, 1000) == 255
    assert pace_s_km(120, 10) == 12000
    assert pace_s_km(100, 0) is None and pace_s_km(100, None) is None


def test_cli(engine, monkeypatch, capsys):
    from app.db import session as sessao
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(sessao, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    assert main([str(ZIP), "--atleta", "Ana"]) == 0
    assert "inseridas=5" in capsys.readouterr().out
    assert main([str(ZIP), "--atleta", "Ana"]) == 0
    assert "inseridas=0 atualizadas=0 ignoradas=5" in capsys.readouterr().out


def test_fuso_min_gravado(session):
    importar(session, ZIP, "Ana")
    fusos = {a.fonte_id: a.fuso_min for a in session.scalars(select(Atividade))}
    assert fusos == {"1000000001": -180, "1000000002": -180, "1000000003": None,
                     "1000000004": None, "1000000005": None}


def test_reimportar_preenche_fuso_das_antigas(session):
    importar(session, ZIP, "Ana")
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    ativ.fuso_min = None  # atividade gravada antes da migracao 0003
    session.commit()
    rel = importar(session, ZIP, "Ana")
    assert rel.atualizadas == 1 and rel.ignoradas == 4
    assert session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one().fuso_min == -180


def test_fonte_sem_horario_local_nao_apaga_fuso_gravado(session, tmp_path):
    importar(session, ZIP, "Ana")
    so_fit = _recortar(tmp_path, set())  # JSON vazio: so os FITs, sem startTimeLocal
    rel = importar(session, so_fit, "Ana")
    assert rel.inseridas == 4  # FIT sem JSON tem outro fonte_id (id derivado)
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    assert ativ.fuso_min == -180


def test_serie_de_ponta_a_ponta(session):
    from app.servicos.evolucao_tiros import serie_tiros_1km
    importar(session, ZIP, "Ana")
    atleta = session.scalars(select(Atleta)).one()
    serie = serie_tiros_1km(session, atleta.id)
    assert len(serie) == 2
    assert [p.n_tiros for p in serie] == [6, 5]
    assert serie[0].pace_s_km == pytest.approx(1505 / 6000 * 1000, abs=0.01)
    assert serie[0].fc_media == pytest.approx(256309 / 1505, abs=0.01)
    assert serie[1].pace_s_km == pytest.approx(237.0, abs=0.01)
    assert serie[1].fc_media == pytest.approx(203546 / 1185, abs=0.01)
    assert importar(session, ZIP, "Ana").inseridas == 0
    assert len(serie_tiros_1km(session, atleta.id)) == 2


def test_importacao_classifica_e_respeita_professor(session):
    importar(session, ZIP, "Ana")
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    ativ.tipo_treino, ativ.tipo_origem = "moderado", "professor"
    session.commit()
    importar(session, ZIP, "Ana")
    ativ = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    assert (ativ.tipo_treino, ativ.tipo_origem) == ("moderado", "professor")


def test_fuso_min_do_parser():
    from datetime import datetime, timedelta, timezone

    from worker.garmin import AtividadeImportada
    from worker.importar_garmin import fuso_min
    inicio = datetime(2025, 3, 5, 1, 30, tzinfo=timezone.utc)

    def ativ(local):
        return AtividadeImportada(fonte_id="x", modalidade="corrida", inicio=inicio, duracao_s=1,
                                  distancia_m=1, fc_media=None, arquivo_bruto=None, inicio_local=local)
    assert fuso_min(ativ(inicio.astimezone(timezone(timedelta(hours=-3))))) == -180
    assert fuso_min(ativ(inicio.astimezone(timezone(timedelta(hours=5, minutes=30))))) == 330
    assert fuso_min(ativ(None)) is None
