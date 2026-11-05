"""Esforços de ciclismo por duração (issue #164; ADR 0008, item 5; nota docs/metricas/esforcos.md).

Dado sintético, valores esperados à mão. Regra própria do projeto, sem artigo.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.metricas.esforcos import (
    ESFORCO,
    FAIXAS_CICLISMO,
    VoltaTreino,
    esforcos_ciclismo,
    faixa_de_duracao,
    montar_blocos,
)

RAIZ = Path(__file__).parents[4]
ORACULO = Path(__file__).with_name("test_esforcos_oraculo.py")
PASTA_FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"


def _voltas(specs):
    """specs: (distancia_m, duracao_s, parada_apos_s[, fc])."""
    voltas, t = [], 0.0
    for i, s in enumerate(specs):
        voltas.append(VoltaTreino(i, t, s[1], s[0], s[3] if len(s) > 3 else None))
        t += s[1] + s[2]
    return voltas


def _esforcos(specs, ref=22):
    return esforcos_ciclismo(montar_blocos(_voltas(specs), "ciclismo", referencia=ref))


@pytest.mark.parametrize("minutos", [1, 2, 3, 4, 5, 8, 10, 12, 15, 20, 30, 40, 60])
def test_faixa_segue_a_formula_max_8pct_15s(minutos):
    # tolerância = max(8% x alvo, 15 s); t4: max(19,2, 15) = 19,2 -> 220,8 a 259,2 (ADR: 221 a 259);
    # t1: max(4,8, 15) = 15 -> 45 a 75; a ADR arredonda ao segundo mais próximo (t12: 662,4 -> 662; 777,6 -> 778).
    alvo = minutos * 60
    tol = max(0.08 * alvo, 15)
    _, lo, hi = next(f for f in FAIXAS_CICLISMO if f[0] == f"t{minutos}")
    assert abs(lo - (alvo - tol)) <= 0.5 and abs(hi - (alvo + tol)) <= 0.5


def test_faixas_nao_se_sobrepoem():
    for (_, _, hi), (_, lo, _) in zip(FAIXAS_CICLISMO, FAIXAS_CICLISMO[1:]):
        assert hi < lo


def test_limites_inclusivos_e_entre_faixas():
    assert faixa_de_duracao(221) == "t4" and faixa_de_duracao(259) == "t4"
    assert faixa_de_duracao(220.9) is None and faixa_de_duracao(259.1) is None
    for d in (30, 90, 400, 1000, 4000):
        assert faixa_de_duracao(d) is None


def test_cinco_x_4_min_fortes_com_2_min_leves():
    # aquecimento 15 min a 25 km/h (6250 m em 900 s), 5 x (2400 m em 240 s = 36 km/h + 733,33 m em 120 s = 22 km/h),
    # 10 min a 24 km/h. Limiar 22 x 1,15 = 25,3 km/h.
    specs = [(6250, 900, 0)] + [(2400, 240, 0), (733.33, 120, 0)] * 5 + [(4000, 600, 0)]
    es = _esforcos(specs)
    assert len(es) == 5
    assert {e.faixa for e in es} == {"t4"}
    assert all(e.velocidade_kmh == pytest.approx(36.0) and e.distancia_m == 2400 for e in es)  # 2400 / 240 x 3,6


def test_20_min_cortados_por_lap_automatico_dao_um_esforco_t20():
    # 5000 m em 750 s + 3000 m em 450 s, mesma velocidade (24 km/h), sem parada: 8000 m em 1200 s.
    specs = [(3000, 600, 0), (5000, 750, 0, 150), (3000, 450, 0, 156), (3000, 600, 0)]
    (e,) = _esforcos(specs, ref=20)
    assert e.faixa == "t20" and e.duracao_s == 1200 and e.distancia_m == 8000
    assert e.velocidade_kmh == pytest.approx(24.0)
    assert e.fc_media == pytest.approx(152.25)  # (150 x 750 + 156 x 450) / 1200 = 182700 / 1200


def test_aquecimento_e_desaquecimento_nao_sao_esforco():
    es = _esforcos([(3000, 600, 0), (8000, 1200, 0), (3000, 600, 0)], ref=20)
    assert [e.faixa for e in es] == ["t20"]


def test_esforco_fora_de_faixa_tem_faixa_none():
    # 6 min (360 s) entre t5 (ate 324) e t8 (a partir de 442): continua esforço, sem faixa.
    # 3600 m em 360 s = 36 km/h >= 20 x 1,15 = 23.
    (e,) = _esforcos([(3000, 600, 0), (3600, 360, 0), (3000, 600, 0)], ref=20)
    assert e.faixa is None and e.duracao_s == 360


def test_sem_esforco():
    assert _esforcos([(5000, 900, 0)] * 3, ref=20) == ()


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


NOMES = ["esforcos_ciclismo_blocos_4min.fit", "esforcos_ciclismo_lap_automatico.fit"]


@pytest.mark.parametrize("nome", NOMES)
def test_esforcos_batem_com_o_oraculo(oraculo, nome):
    modalidade, ref, esperados = oraculo.ESPERADO[nome]
    fit = ler_fit((PASTA_FIT / nome).read_bytes())
    voltas = [
        VoltaTreino(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media, v.intensidade)
        for v in fit.voltas
    ]
    es = esforcos_ciclismo(montar_blocos(voltas, modalidade, referencia=ref))
    do_oraculo = [e for e in esperados if e.categoria == ESFORCO]
    assert len(es) == len(do_oraculo)
    for e, o in zip(es, do_oraculo):
        assert e.faixa == o.faixa
        assert (e.volta_inicial, e.volta_final) == (o.volta_inicial, o.volta_final)
        assert e.duracao_s == pytest.approx(o.duracao_s, abs=1e-6)
        assert e.velocidade_kmh == pytest.approx(o.intensidade, abs=1e-3)
        assert e.fc_media == pytest.approx(o.fc_media, abs=1e-6)
    assert [e.faixa for e in es] == (["t4"] * 5 if "4min" in nome else ["t20"])
