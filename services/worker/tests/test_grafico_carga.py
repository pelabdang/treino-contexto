"""Gráfico e CSV da carga (issue #143), com as fixtures sintéticas de ``tests/fixtures/garmin/carga/``.

Valores esperados: oráculo da #137 (``CARGA_DIA`` e ``SERIE`` de test_carga_oraculo, contas à mão em
docs/metricas/carga-oraculo.md). O PNG é teste de fumaça (assinatura e tamanho).
"""

import csv
import importlib.util
import os
import struct
import sys
from datetime import date
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atleta
from app.graficos.carga import COLUNAS_CSV, TEXTO_VAZIO, linhas_csv, render_png
from app.ingestao.importacao import importar
from app.ingestao.saude import importar_saude
from app.metricas.serie_carga import AtividadeCarga, calcular_serie
from app.servicos.carga import calcular_carga_do_atleta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from worker import grafico_carga
from worker.grafico_carga import AtletaInexistente, gerar

RAIZ = Path(__file__).resolve().parents[3]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "carga" / "exportacao_carga.zip"
ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

_spec = importlib.util.spec_from_file_location(
    "_carga_oraculo_g", RAIZ / "services" / "api" / "tests" / "metricas" / "test_carga_oraculo.py")
_o = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _o
_spec.loader.exec_module(_o)
CARGA_DIA, SERIE, PRIMEIRO_DIA, ULTIMO_DIA = _o.CARGA_DIA, _o.SERIE, _o.PRIMEIRO_DIA, _o.ULTIMO_DIA


@pytest.fixture
def session():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        yield s
    Base.metadata.drop_all(eng)
    eng.dispose()


def _atleta_com_carga(session) -> int:
    importar(session, str(ZIP), "Ana")
    importar_saude(session, str(ZIP), "Ana")
    atleta_id = session.scalars(select(Atleta)).one().id
    calcular_carga_do_atleta(session, atleta_id)
    return atleta_id


def _ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_bate_com_o_oraculo(session, tmp_path):
    atleta_id = _atleta_com_carga(session)
    png, arq_csv, sem_linha = gerar(session, atleta_id, pasta=tmp_path / "entregas" / "meta-6")
    assert (png.name, arq_csv.name) == (f"carga-atleta-{atleta_id}.png", f"carga-atleta-{atleta_id}.csv")
    assert sem_linha == 0
    linhas = _ler(arq_csv)
    assert tuple(linhas[0]) == COLUNAS_CSV
    por_dia = {date.fromisoformat(r["dia"]): r for r in linhas}
    # 05/03 a 16/04 = 43 dias, um por dia (inclusive os sem treino)
    assert len(linhas) == 43 and min(por_dia) == PRIMEIRO_DIA and max(por_dia) == ULTIMO_DIA
    for dia, e in SERIE.items():
        r = por_dia[dia]
        assert float(r["carga"]) == pytest.approx(e.carga, abs=1e-6), dia
        assert float(r["ctl"]) == pytest.approx(e.ctl, abs=1e-6), dia
        assert float(r["atl"]) == pytest.approx(e.atl, abs=1e-6), dia
        assert float(r["tsb"]) == pytest.approx(e.tsb, abs=1e-6), dia
        assert r["aprendendo"] == ("sim" if e.aprendendo else "nao"), dia
        assert (int(r["atividades"]), int(r["calculadas"]), int(r["sem_carga"])) == (
            e.atividades, e.calculadas, e.sem_carga), dia
    for dia, carga in CARGA_DIA.items():
        assert float(por_dia[dia]["carga"]) == pytest.approx(carga, abs=1e-6), dia


def test_png_de_fumaca(session, tmp_path):
    atleta_id = _atleta_com_carga(session)
    png, _, _ = gerar(session, atleta_id, pasta=tmp_path)
    dados = png.read_bytes()
    assert dados.startswith(ASSINATURA_PNG)
    assert struct.unpack(">II", dados[16:24]) == (1600, 1200)


def test_recorte_mantem_os_valores_da_serie_inteira(session, tmp_path):
    atleta_id = _atleta_com_carga(session)
    _, arq_csv, _ = gerar(session, atleta_id, inicio=date(2025, 4, 1), fim=date(2025, 4, 16), pasta=tmp_path)
    linhas = _ler(arq_csv)
    assert [r["dia"] for r in linhas][0] == "2025-04-01" and len(linhas) == 16
    ultimo = linhas[-1]
    assert float(ultimo["ctl"]) == pytest.approx(SERIE[date(2025, 4, 16)].ctl, abs=1e-6)


def test_atleta_inexistente(session, tmp_path):
    with pytest.raises(AtletaInexistente):
        gerar(session, 999, pasta=tmp_path)


def test_serie_vazia_gera_png_e_csv_so_com_cabecalho(session, tmp_path):
    session.add(Atleta(nome="Vazio"))
    session.commit()
    atleta_id = session.scalars(select(Atleta)).one().id
    png, arq_csv, _ = gerar(session, atleta_id, pasta=tmp_path)
    assert png.read_bytes().startswith(ASSINATURA_PNG)
    assert _ler(arq_csv) == []
    assert TEXTO_VAZIO  # o texto desenhado no PNG vazio


def test_linhas_csv_contas_a_mao():
    # carga 100 no primeiro dia: CTL = 100 x 0,023528 = 2,3528; ATL = 100 x 0,133122 = 13,3122; TSB = -10,9594
    s = calcular_serie([AtividadeCarga(date(2025, 1, 6), 100.0)])
    (linha,) = linhas_csv(s.dias)
    assert linha["dia"] == "2025-01-06" and linha["aprendendo"] == "sim"
    assert float(linha["ctl"]) == pytest.approx(2.3528, abs=1e-4)
    assert float(linha["atl"]) == pytest.approx(13.3122, abs=1e-4)
    assert float(linha["tsb"]) == pytest.approx(-10.9594, abs=1e-4)
    assert linha["carga"] == "100.000000"


def test_render_png_dia_com_treino_sem_carga_e_depois_dos_42_dias():
    # 50 dias: cobre o ramo em que "aprendendo" termina e o marcador de dia sem carga
    ativ = [AtividadeCarga(date(2025, 1, 6), 80.0), AtividadeCarga(date(2025, 2, 20), motivo="sem_fc")]
    dias = calcular_serie(ativ).dias
    assert len(dias) == 46 and not dias[-1].aprendendo
    assert render_png(dias, "Ana").startswith(ASSINATURA_PNG)


def test_cli_sem_atleta_devolve_1(monkeypatch, session, capsys, tmp_path):
    from app.db import session as sessao
    monkeypatch.setattr(sessao, "SessionLocal", lambda: session)
    assert grafico_carga.main(["--atleta-id", "999", "--saida", str(tmp_path)]) == 1
    assert "não encontrado" in capsys.readouterr().err
