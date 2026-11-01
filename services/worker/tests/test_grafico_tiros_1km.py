"""Comando do gráfico dos tiros (issue #15), com as fixtures importadas no banco.

Valores esperados: oráculo da #30 (contas à mão em
services/api/tests/metricas/test_oraculo_fixtures.py):
  1000000001: 1505/6000 x 1000 = 250,83 s/km -> "250.8" e "4:11"; FC 256309/1505 = 170,30 -> "170.3"
  1000000002: 1185/5000 x 1000 = 237,0 s/km -> "237.0" e "3:57"; FC 203546/1185 = 171,77 -> "171.8"
"""

import csv
import os
import struct
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atleta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import worker.grafico_tiros_1km as cmd
from worker.grafico_tiros_1km import AtletaInexistente, gerar
from worker.importar_garmin import importar

RAIZ = Path(__file__).resolve().parents[3]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


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


def _ler_csv(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_fixtures_geram_png_e_csv_do_oraculo(session, tmp_path):
    importar(session, ZIP, "Atleta Ficticio")
    atleta = session.query(Atleta).one()
    png, arq_csv = gerar(session, atleta.id, pasta=tmp_path / "entregas" / "meta-1")

    assert png.name == f"tiros-1km-atleta-{atleta.id}.png"
    assert arq_csv.name == f"tiros-1km-atleta-{atleta.id}.csv"
    dados = png.read_bytes()
    assert dados.startswith(ASSINATURA_PNG)
    assert struct.unpack(">II", dados[16:24]) == (1600, 1000)

    linhas = _ler_csv(arq_csv)
    assert list(linhas[0]) == [
        "data", "atividade_id", "n_tiros", "pace_medio_s_km", "pace_medio_min_km", "fc_media",
    ]
    assert len(linhas) == 2
    a, b = linhas  # ordenadas por data: 04/03 e 11/03 (fixtures)
    assert (a["n_tiros"], a["pace_medio_s_km"], a["pace_medio_min_km"], a["fc_media"]) == (
        "6", "250.8", "4:11", "170.3")
    assert (b["n_tiros"], b["pace_medio_s_km"], b["pace_medio_min_km"], b["fc_media"]) == (
        "5", "237.0", "3:57", "171.8")
    assert a["data"] < b["data"]


def test_filtro_de_periodo(session, tmp_path):
    importar(session, ZIP, "Atleta Ficticio")
    atleta = session.query(Atleta).one()
    from datetime import date

    _, arq_csv = gerar(session, atleta.id, inicio=date(2025, 3, 10), pasta=tmp_path)
    (so_b,) = _ler_csv(arq_csv)
    assert so_b["pace_medio_min_km"] == "3:57"


def test_atleta_sem_sessoes_gera_png_e_csv_so_com_cabecalho(session, tmp_path):
    atleta = Atleta(nome="Sem Treinos")
    session.add(atleta)
    session.commit()
    png, arq_csv = gerar(session, atleta.id, pasta=tmp_path)
    assert png.read_bytes().startswith(ASSINATURA_PNG)
    assert _ler_csv(arq_csv) == []
    assert arq_csv.read_text(encoding="utf-8").strip() == (
        "data,atividade_id,n_tiros,pace_medio_s_km,pace_medio_min_km,fc_media"
    )


def test_atleta_inexistente(session, tmp_path):
    with pytest.raises(AtletaInexistente):
        gerar(session, 999, pasta=tmp_path)
    assert not list(tmp_path.iterdir())  # nada gravado


def test_main_atleta_inexistente_sai_com_erro(engine, tmp_path, monkeypatch, capsys):
    import app.db.session as sessao

    monkeypatch.setattr(sessao, "SessionLocal", lambda: Session(engine))
    codigo = cmd.main(["--atleta-id", "999", "--saida", str(tmp_path)])
    assert codigo == 1
    assert "999" in capsys.readouterr().err


def test_main_grava_arquivos(engine, tmp_path, monkeypatch, capsys):
    import app.db.session as sessao

    monkeypatch.setattr(sessao, "SessionLocal", lambda: Session(engine))
    with Session(engine) as s:
        importar(s, ZIP, "Atleta Ficticio")
        atleta_id = s.query(Atleta).one().id
    saida = tmp_path / "x" / "meta-1"
    assert cmd.main(["--atleta-id", str(atleta_id), "--saida", str(saida)]) == 0
    assert (saida / f"tiros-1km-atleta-{atleta_id}.png").exists()
    assert len(_ler_csv(saida / f"tiros-1km-atleta-{atleta_id}.csv")) == 2


def test_data_invalida_na_linha_de_comando(capsys):
    with pytest.raises(SystemExit) as e:
        cmd.main(["--atleta-id", "1", "--inicio", "31/10/2025"])
    assert e.value.code == 2
