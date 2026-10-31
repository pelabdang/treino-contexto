"""Confere as fixtures sinteticas da exportacao Garmin (issue #8)."""

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import Intensity

PASTA = Path(__file__).parent / "fixtures" / "garmin"
ZIP = PASTA / "exportacao_minima.zip"


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures", PASTA / "gerar_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fits() -> dict[str, bytes]:
    with zipfile.ZipFile(ZIP) as z:
        interno = [n for n in z.namelist() if n.endswith(".zip")]
        assert len(interno) == 1
        with zipfile.ZipFile(io.BytesIO(z.read(interno[0]))) as zi:
            return {n: zi.read(n) for n in zi.namelist()}


def test_zip_tem_json_e_quatro_fit():
    with zipfile.ZipFile(ZIP) as z:
        jsons = [n for n in z.namelist() if n.endswith("summarizedActivities.json")]
        assert len(jsons) == 1
        dados = json.loads(z.read(jsons[0]))
    assert len(dados[0]["summarizedActivitiesExport"]) == 5
    fits = _fits()
    assert len(fits) == 4
    assert all(n.endswith(".fit") for n in fits)


def test_geracao_e_deterministica(gerador, tmp_path):
    gerador.main(tmp_path / "a")
    gerador.main(tmp_path / "b")
    a = (tmp_path / "a" / "exportacao_minima.zip").read_bytes()
    assert a == (tmp_path / "b" / "exportacao_minima.zip").read_bytes()
    assert a == ZIP.read_bytes(), "fixture versionada desatualizada: rode gerar_fixtures.py"


def test_voltas_do_intervalado_6x1km():
    fit = FitFile.from_bytes(_fits()["atleta-ficticio_1000000001.fit"])
    laps = [r.message for r in fit.records if isinstance(r.message, LapMessage)]
    assert len(laps) == 13
    tiros = [l for l in laps if l.intensity == Intensity.ACTIVE.value]
    assert len(tiros) == 6
    assert all(round(l.total_distance) == 1000 for l in tiros)


def test_sem_gps_e_sem_dado_pessoal():
    for conteudo in _fits().values():
        fit = FitFile.from_bytes(conteudo)
        for r in fit.records:
            if isinstance(r.message, RecordMessage):
                assert r.message.position_lat is None and r.message.position_long is None
    with zipfile.ZipFile(ZIP) as z:
        texto = z.read([n for n in z.namelist() if n.endswith(".json")][0]).decode()
    assert "@" not in texto and "lat" not in texto.lower()
