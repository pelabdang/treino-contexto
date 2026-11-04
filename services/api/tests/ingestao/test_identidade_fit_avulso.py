"""Identidade do FIT avulso importado depois do JSON, e o inverso (issue #133, ADR 0006).

Dado sintetico: pares JSON x FIT das fixtures do clima (Meta 4) e da exportacao minima (Meta 3).
A exclusao "exportacao nao casa com exportacao" so vale quando os dois lados tem `activityId`.
"""

import json
import shutil
from pathlib import Path

import pytest
from app.db.models import Atividade
from app.ingestao.importacao import importar
from sqlalchemy import func, select

RAIZ = Path(__file__).resolve().parents[4]
CLIMA = RAIZ / "tests" / "fixtures" / "clima"
GARMIN = RAIZ / "tests" / "fixtures" / "garmin"
ZIP = GARMIN / "exportacao_minima.zip"
ID_CLIMA = "3000000101"  # JSON; o FIT corrida_ar_livre comeca no mesmo instante


def _itens_clima() -> list[dict]:
    return json.loads((CLIMA / "exportacao_clima.json").read_text())[0]["summarizedActivitiesExport"]


def _json_clima(destino: Path) -> Path:
    itens = [i for i in _itens_clima() if str(i["activityId"]) == ID_CLIMA]
    destino.write_text(json.dumps([{"summarizedActivitiesExport": itens}]))
    return destino


def _fit_avulso(destino: Path) -> Path:
    shutil.copy(CLIMA / "fit" / "corrida_ar_livre.fit", destino)
    return destino


def _linhas(session):
    return list(session.scalars(select(Atividade).order_by(Atividade.id)))


def _n(session) -> int:
    return session.scalar(select(func.count()).select_from(Atividade))


def _foto(a: Atividade) -> tuple:
    return (a.id, a.fonte, a.fonte_id, a.inicio, a.duracao_s, a.arquivo_bruto, len(a.segmentos))


def test_json_e_depois_fit_avulso_do_mesmo_treino_da_uma_linha(session, tmp_path):
    importar(session, _json_clima(tmp_path / "a.json"), "Ana")
    (original,) = _linhas(session)
    assert original.fonte_id == ID_CLIMA
    rel = importar(session, _fit_avulso(tmp_path / "avulso.fit"), "Ana")
    assert (rel.inseridas, rel.atualizadas) == (0, 1)
    (linha,) = _linhas(session)
    assert (linha.id, linha.fonte, linha.fonte_id) == (original.id, "garmin_export", ID_CLIMA)  # activityId fica


def test_fit_avulso_e_depois_json_da_uma_linha_com_o_activity_id(session, tmp_path):
    importar(session, _fit_avulso(tmp_path / "avulso.fit"), "Ana")
    (avulsa,) = _linhas(session)
    assert avulsa.fonte_id.startswith("fit-")
    rel = importar(session, _json_clima(tmp_path / "a.json"), "Ana")
    assert (rel.inseridas, rel.atualizadas) == (0, 1)
    (linha,) = _linhas(session)
    assert (linha.id, linha.fonte, linha.fonte_id) == (avulsa.id, "garmin_export", ID_CLIMA)


@pytest.mark.parametrize("ordem", ["json_primeiro", "fit_primeiro"])
def test_reimportar_nao_muda_nada(session, tmp_path, ordem):
    j, f = _json_clima(tmp_path / "a.json"), _fit_avulso(tmp_path / "avulso.fit")
    primeiro, segundo = (j, f) if ordem == "json_primeiro" else (f, j)
    importar(session, primeiro, "Ana")
    importar(session, segundo, "Ana")
    (antes,) = _linhas(session)
    snapshot = _foto(antes)
    for caminho in (primeiro, segundo, primeiro, segundo):
        rel = importar(session, caminho, "Ana")
        assert (rel.inseridas, rel.atualizadas, rel.ignoradas) == (0, 0, 1), caminho
    (depois,) = _linhas(session)
    assert _foto(depois) == snapshot


def test_json_da_meta_3_e_depois_fit_avulso_30_s_depois(session, tmp_path):
    importar(session, ZIP, "Ana")
    antes = _n(session)
    original = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    esperado = (original.fonte_id, original.inicio, len(original.segmentos), original.fuso_min)
    avulso = tmp_path / "avulso.fit"
    shutil.copy(GARMIN / "fit" / "upload_mesma_atividade_1000000001.fit", avulso)
    importar(session, avulso, "Ana")
    assert _n(session) == antes
    session.refresh(original)
    # o JSON e mais rico: nada dele e reescrito pelo FIT
    assert (original.fonte_id, original.inicio, len(original.segmentos), original.fuso_min) == esperado


def test_duas_atividades_da_exportacao_com_activity_id_diferente_a_30_s_continuam_duas(session, tmp_path):
    base = next(i for i in _itens_clima() if str(i["activityId"]) == ID_CLIMA)
    outra = dict(base, activityId=3000000999, startTimeGmt=base["startTimeGmt"] + 30_000,
                 beginTimestamp=base["beginTimestamp"] + 30_000)
    arq = tmp_path / "duas.json"
    arq.write_text(json.dumps([{"summarizedActivitiesExport": [base, outra]}]))
    rel = importar(session, arq, "Ana")
    assert rel.inseridas == 2 and _n(session) == 2
    rel2 = importar(session, arq, "Ana")
    assert (rel2.inseridas, rel2.atualizadas, rel2.ignoradas) == (0, 0, 2) and _n(session) == 2


def test_fit_avulso_nao_casa_com_outro_atleta(session, tmp_path):
    importar(session, _json_clima(tmp_path / "a.json"), "Ana")
    importar(session, _fit_avulso(tmp_path / "avulso.fit"), "Bia")
    assert _n(session) == 2
