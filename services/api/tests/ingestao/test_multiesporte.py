"""Subtipos multiesporte_pai e troca (issue #230, ADR 0009). Fixtures sinteticas em tests/fixtures/multiesporte/."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta
from app.ingestao.garmin import ler_exportacao, tipos
from app.ingestao.importacao import importar
from app.metricas.transicao import VERSAO, AtividadeLeve, sugerir_transicao

PASTA = Path(__file__).resolve().parents[3].parent / "tests" / "fixtures" / "multiesporte"
JSON = PASTA / "exportacao_multiesporte.json"


@pytest.mark.parametrize("activity_type,sport_type,esperado", [
    ("multi_sport", None, ("outra", "multiesporte_pai")),
    ("MULTI_SPORT", "MULTI_SPORT", ("outra", "multiesporte_pai")),
    ("triathlon", None, ("outra", "multiesporte_pai")),
    ("duathlon", None, ("outra", "multiesporte_pai")),
    (None, "MULTISPORT", ("outra", "multiesporte_pai")),
    ("transition", "TRANSITION", ("outra", "troca")),
    ("running", "RUNNING", ("corrida", None)),
    ("treadmill_running", "RUNNING", ("corrida", "esteira")),
    ("open_water_swimming", "SWIMMING", ("natacao", "aguas_abertas")),
    ("road_biking", "CYCLING", ("ciclismo", None)),
    ("yoga", "FITNESS_EQUIPMENT", ("outra", None)),
    (None, None, ("outra", None)),
])
def test_de_json(activity_type, sport_type, esperado):
    assert tipos.de_json(activity_type, sport_type) == esperado


@pytest.mark.parametrize("sport,sub_sport,esperado", [
    ("multisport", "triathlon", ("outra", "multiesporte_pai")),
    ("multisport", None, ("outra", "multiesporte_pai")),
    ("transition", "generic", ("outra", "troca")),
    ("running", "treadmill", ("corrida", "esteira")),
    ("swimming", "lap_swimming", ("natacao", "piscina")),
    ("training", None, ("outra", None)),
    (None, None, ("outra", None)),
])
def test_de_fit(sport, sub_sport, esperado):
    assert tipos.de_fit(sport, sub_sport) == esperado


def test_json_sintetico_le_pai_e_trocas():
    por_id = {a.fonte_id: a for a in ler_exportacao(JSON)}
    assert {i: (a.modalidade, a.subtipo) for i, a in por_id.items()} == {
        "3000000201": ("outra", "multiesporte_pai"),
        "3000000202": ("natacao", "aguas_abertas"),
        "3000000203": ("outra", "troca"),
        "3000000204": ("ciclismo", None),
        "3000000205": ("outra", "troca"),
        "3000000206": ("corrida", None),
        "3000000207": ("corrida", None),
    }


@pytest.mark.parametrize("nome,subtipo", [("multiesporte_pai.fit", "multiesporte_pai"), ("troca.fit", "troca")])
def test_fit_sintetico(nome, subtipo):
    [a] = ler_exportacao(PASTA / "fit" / nome)
    assert (a.modalidade, a.subtipo) == ("outra", subtipo)


def test_importar_grava_outra_com_subtipo_e_nao_descarta(session):
    importar(session, JSON, "Atleta Ficticio")
    linhas = {a.fonte_id: (a.modalidade, a.subtipo) for a in session.query(Atividade)}
    assert len(linhas) == 7
    assert linhas["3000000201"] == ("outra", "multiesporte_pai")
    assert linhas["3000000203"] == ("outra", "troca")


def _leves(session):
    return [AtividadeLeve(a.id, a.modalidade, a.inicio.replace(tzinfo=UTC), a.duracao_s)
            for a in session.query(Atividade)]


def test_transicao_1_nao_muda_com_pai_e_troca(session):
    """`outra` fica fora da regra: o resultado e o mesmo com e sem pai/troca (e com subtipo nulo)."""
    assert VERSAO == "transicao@1"
    importar(session, JSON, "Atleta Ficticio")
    ids = {a.fonte_id: a.id for a in session.query(Atividade)}
    com = sugerir_transicao(_leves(session))
    sem = sugerir_transicao([a for a in _leves(session) if a.modalidade != "outra"])
    assert com == sem == {ids["3000000202"], ids["3000000204"], ids["3000000206"]}
    # mesmo resultado se os subtipos fossem nulos (como antes do #230)
    session.query(Atividade).filter(Atividade.modalidade == "outra").update({"subtipo": None})
    assert sugerir_transicao(_leves(session)) == com
