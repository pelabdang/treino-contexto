"""QA de ponta a ponta da Meta 1 com as fixtures sintéticas (issue #18).

Roda o fluxo documentado como o usuário roda, num SQLite em arquivo temporário:
migrações (alembic) -> importação (CLI) -> gráfico (CLI) -> API (JSON e PNG),
e confere tudo contra ``ESPERADO`` do oráculo da #30 (não repete os números).
"""

import csv
import importlib.util
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
ORACULO = RAIZ / "services" / "api" / "tests" / "metricas" / "test_oraculo_fixtures.py"
ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_fixtures", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ORA = _oraculo()
# (id da atividade na fonte, n_tiros, pace s/km, FC bpm), na ordem das datas
ESPERADO = [(str(i), *v) for i, v in ORA.ESPERADO.items()]
FORA = [str(i) for i in ORA.FORA_DA_SERIE]


def _roda(args, env, cwd):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r.stdout


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    base = tmp_path_factory.mktemp("e2e")
    url = f"sqlite:///{base / 'treino.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    return env, url, base


def _importar(env):
    return _roda(["-m", "worker.importar_garmin", str(ZIP), "--atleta", "Atleta Ficticio"], env, RAIZ)


def _contagens(url):
    from app.db.models import Atividade, Segmento

    eng = create_engine(url)
    with Session(eng) as s:
        n = (s.scalar(select(func.count()).select_from(Atividade)),
             s.scalar(select(func.count()).select_from(Segmento)))
    eng.dispose()
    return n


def test_fluxo_completo(ambiente):
    env, url, base = ambiente

    # importar
    assert "inseridas=5 atualizadas=0 ignoradas=0" in _importar(env)
    ativ1, seg1 = _contagens(url)
    assert ativ1 == 5 and seg1 == 36

    # gráfico (CLI): PNG 1600x1000 e CSV com 2 linhas
    from app.db.models import Atleta

    eng = create_engine(url)
    with Session(eng) as s:
        atleta_id = s.scalars(select(Atleta)).one().id
    saida = base / "entregas" / "meta-1"
    _roda(["-m", "worker.grafico_tiros_1km", "--atleta-id", str(atleta_id), "--saida", str(saida)], env, RAIZ)
    png_cli = (saida / f"tiros-1km-atleta-{atleta_id}.png").read_bytes()
    assert png_cli.startswith(ASSINATURA_PNG)
    assert struct.unpack(">II", png_cli[16:24]) == (1600, 1000)
    with (saida / f"tiros-1km-atleta-{atleta_id}.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == len(ESPERADO)

    # API: JSON e PNG, sobre o mesmo banco
    from app.db.session import get_session
    from app.main import app

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    try:
        client = TestClient(app)
        r = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km")
        assert r.status_code == 200
        sessoes = r.json()["sessoes"]
        assert len(sessoes) == len(ESPERADO)
        for sess, (_, n, pace, fc) in zip(sessoes, ESPERADO):
            assert sess["n_tiros"] == n
            assert sess["pace_medio_s_km"] == pytest.approx(pace, abs=0.05)
            assert sess["fc_media"] == pytest.approx(fc, abs=0.05)
        assert [s["pace_medio"] for s in sessoes] == ["4:11", "3:57"]

        rp = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km.png")
        assert rp.status_code == 200 and rp.headers["content-type"] == "image/png"
        assert rp.content == png_cli  # API e comando usam o mesmo render_png
    finally:
        app.dependency_overrides.clear()

    # fora da série: rodagem com auto-lap, natação e esteira sem FIT
    from app.db.models import Atividade

    with Session(eng) as s:
    # ids do banco das atividades da série
        na_serie = {s_["atividade_id"] for s_ in sessoes}
        fontes_serie = {
            s.get(Atividade, i).fonte_id for i in na_serie
        }
    assert fontes_serie == {e[0] for e in ESPERADO}
    assert not fontes_serie & set(FORA)

    # reimportar: nada duplica, série igual
    assert "inseridas=0" in _importar(env)
    assert _contagens(url) == (ativ1, seg1)
    app.dependency_overrides[get_session] = sessao
    try:
        assert TestClient(app).get(f"/atletas/{atleta_id}/evolucao/tiros-1km").json()["sessoes"] == sessoes
    finally:
        app.dependency_overrides.clear()
        eng.dispose()
