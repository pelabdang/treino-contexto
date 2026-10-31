"""Testes do desenho do gráfico, do CSV e do m:ss (issue #39). Sem banco.

Pontos do oráculo da #30 (contas à mão em test_oraculo_fixtures.py):
  1000000001: 6 tiros, 1505/6000 x 1000 = 250,8333 s/km (-> "4:11"), FC 256309/1505 = 170,3050
  1000000002: 5 tiros, 1185/5000 x 1000 = 237,0 s/km (-> "3:57"), FC 203546/1185 = 171,7688
m:ss: 250,8333 + 0,5 = 251,33 -> piso 251 s = 4 min 11 s; 237,0 + 0,5 -> 237 s = 3 min 57 s.
"""

import struct
from datetime import date

import pytest

from app.graficos.tiros_1km import COLUNAS_CSV, linhas_csv, render_png
from app.metricas.tiros_1km import PontoSessao, formatar_pace

ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

A = PontoSessao(1000000001, date(2025, 3, 4), 6, 1505 / 6000 * 1000, 256309 / 1505)
B = PontoSessao(1000000002, date(2025, 3, 11), 5, 1185 / 5000 * 1000, 203546 / 1185)


def _tamanho(png: bytes) -> tuple[int, int]:
    return struct.unpack(">II", png[16:24])  # IHDR: largura, altura


@pytest.mark.parametrize(
    ("s_km", "esperado"),
    [
        (238.8, "3:59"),
        (239.5, "4:00"),  # nunca "3:60"
        (238.49, "3:58"),
        (250.83, "4:11"),
        (237.0, "3:57"),
        (59.5, "1:00"),
        (238.5, "3:59"),  # meio para cima (round() daria 238 = "3:58")
    ],
)
def test_formatar_pace(s_km, esperado):
    assert formatar_pace(s_km) == esperado


def test_png_com_dois_pontos():
    png = render_png([A, B], "Atleta Fictício")
    assert png.startswith(ASSINATURA_PNG)
    assert _tamanho(png) == (1600, 1000)


def test_png_serie_vazia_nao_da_erro():
    png = render_png([], "Atleta Fictício")
    assert png.startswith(ASSINATURA_PNG)
    assert _tamanho(png) == (1600, 1000)


def test_png_sessao_sem_fc_e_sessao_unica():
    sem_fc = PontoSessao(1, date(2025, 3, 4), 4, 240.0, None)
    for serie in ([A, sem_fc], [sem_fc], [sem_fc, B]):
        png = render_png(serie, "Atleta Fictício")
        assert png.startswith(ASSINATURA_PNG)
        assert _tamanho(png) == (1600, 1000)


def test_png_muitas_sessoes():
    serie = [PontoSessao(i, date(2025, 1, 1 + i), 5, 240.0 - i, 160.0 + i) for i in range(30)]
    assert _tamanho(render_png(serie, "Atleta Fictício")) == (1600, 1000)


def test_linhas_csv():
    linhas = linhas_csv([A, B])
    assert len(linhas) == 2
    assert tuple(linhas[0]) == COLUNAS_CSV == (
        "data", "atividade_id", "n_tiros", "pace_medio_s_km", "pace_medio_min_km", "fc_media",
    )
    assert linhas[0] == {
        "data": "2025-03-04",
        "atividade_id": "1000000001",
        "n_tiros": "6",
        "pace_medio_s_km": "250.8",
        "pace_medio_min_km": "4:11",
        "fc_media": "170.3",
    }
    assert linhas[1] == {
        "data": "2025-03-11",
        "atividade_id": "1000000002",
        "n_tiros": "5",
        "pace_medio_s_km": "237.0",
        "pace_medio_min_km": "3:57",
        "fc_media": "171.8",
    }


def test_linhas_csv_fc_vazia_quando_sem_fc():
    (linha,) = linhas_csv([PontoSessao(1, date(2025, 3, 4), 4, 240.0, None)])
    assert linha["fc_media"] == ""
