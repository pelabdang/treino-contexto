"""QA de ponta a ponta da Meta 2 com as fixtures sintéticas (issue #72).

Migrações (alembic) -> importação (CLI) -> endpoint JSON -> compara com o exemplo de contrato do cliente TypeScript
(``packages/api-client/exemplos/evolucao-tiros-1km.json``) e confere 404, período vazio e o PNG, num SQLite temporário.
"""

import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
EXEMPLO = RAIZ / "packages" / "api-client" / "exemplos" / "evolucao-tiros-1km.json"


def _roda(args, env, cwd):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r.stdout


@pytest.fixture(scope="module")
def client_e_atleta(tmp_path_factory):
    from app.db.models import Atleta
    from app.db.session import get_session
    from app.main import app

    base = tmp_path_factory.mktemp("e2e_meta2")
    url = f"sqlite:///{base / 'treino.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    saida = _roda(["-m", "worker.importar_garmin", str(ZIP), "--atleta", "Atleta Ficticio"], env, RAIZ)
    assert "inseridas=5 atualizadas=0 ignoradas=0" in saida
    eng = create_engine(url)
    with Session(eng) as s:
        atleta_id = s.scalars(select(Atleta)).one().id

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    try:
        yield TestClient(app), atleta_id
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def test_json_igual_ao_exemplo_do_contrato(client_e_atleta):
    client, atleta_id = client_e_atleta
    r = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km")
    assert r.status_code == 200
    assert r.json() == json.loads(EXEMPLO.read_text(encoding="utf-8"))


def test_textos_de_pace_e_versao(client_e_atleta):
    client, atleta_id = client_e_atleta
    j = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km").json()
    assert j["versao_calculo"] == "tiros_1km@6" and j["reclassificacao_pendente"] is False
    assert [s["pace_medio"] for s in j["sessoes"]] == ["4:11", "3:57"]
    assert [s["data"] for s in j["sessoes"]] == ["2025-03-04", "2025-03-11"]
    assert [s["pace_melhor"] for s in j["sessoes"]] == ["4:08", "3:54"]
    assert [s["fc_melhor_tiro"] for s in j["sessoes"]] == [175.0, 177.0]
    # escala mínima: 5 bpm na FC e 30 s/km no pace
    assert j["eixos"]["fc"]["max_bpm"] - j["eixos"]["fc"]["min_bpm"] >= 5 - 1e-6
    assert j["eixos"]["pace"]["max_s_km"] - j["eixos"]["pace"]["min_s_km"] >= 30 - 1e-6


def test_atleta_inexistente_404(client_e_atleta):
    client, _ = client_e_atleta
    r = client.get("/atletas/99/evolucao/tiros-1km")
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}


def test_periodo_sem_sessoes_vazio(client_e_atleta):
    client, atleta_id = client_e_atleta
    r = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km", params={"inicio": "2030-01-01", "fim": "2030-12-31"})
    assert r.status_code == 200 and r.json()["sessoes"] == []


def test_png_1600x1000(client_e_atleta):
    client, atleta_id = client_e_atleta
    r = client.get(f"/atletas/{atleta_id}/evolucao/tiros-1km.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert struct.unpack(">II", r.content[16:24]) == (1600, 1000)
