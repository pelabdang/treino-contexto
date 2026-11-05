"""Esforços de corrida por distância (issue #163; ADR 0008, item 5; nota docs/metricas/esforcos.md).

Dado sintético. Valores esperados calculados à mão (comentários). Regra própria do projeto, sem artigo.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.metricas.esforcos import (
    ESFORCO,
    FAIXAS_CORRIDA,
    VoltaTreino,
    esforcos_corrida,
    faixa_de_distancia,
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


def _esforcos(specs, ref=330):
    return esforcos_corrida(montar_blocos(_voltas(specs), "corrida", referencia=ref))


@pytest.mark.parametrize("alvo", [200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000, 3000, 5000])
def test_faixa_segue_a_formula_max_5pct_30m(alvo):
    # tolerância = max(5% x alvo, 30 m); d800 -> max(40, 30) = 40 -> 760 a 840; d200 -> max(10, 30) = 30 -> 170 a 230
    tol = max(0.05 * alvo, 30)
    _, lo, hi = next(f for f in FAIXAS_CORRIDA if f[0] == f"d{alvo}")
    assert lo == pytest.approx(alvo - tol)
    assert hi == pytest.approx(alvo + tol)


def test_faixas_nao_se_sobrepoem_e_estao_em_ordem():
    for (_, _, hi), (_, lo, _) in zip(FAIXAS_CORRIDA, FAIXAS_CORRIDA[1:]):
        assert hi < lo


def test_limites_da_d800_sao_inclusivos():
    assert faixa_de_distancia(760) == "d800"
    assert faixa_de_distancia(840) == "d800"
    assert faixa_de_distancia(759.9) is None
    assert faixa_de_distancia(840.1) is None


@pytest.mark.parametrize(
    "dist,faixa",
    [(170, "d200"), (230, "d200"), (400, "d400"), (1050, "d1000"), (1575, "d1500"), (5250, "d5000")],
)
def test_extremos_e_alvos(dist, faixa):
    assert faixa_de_distancia(dist) == faixa


@pytest.mark.parametrize("dist", [100, 250, 700, 900, 1100, 1350, 1700, 2500, 4000, 8000])
def test_entre_faixas_ou_fora_nao_tem_faixa(dist):
    # ADR: esforço fora de qualquer faixa continua esforço, com faixa None e a distância real.
    assert faixa_de_distancia(dist) is None


def test_dez_x_400_com_pausa_dao_dez_esforcos_d400():
    # 2 km a 330 s/km, 10 x 400 m em 88 s (220 s/km <= 297) com 90 s parado, 1 km a 340 s/km.
    specs = [(2000, 660, 0)] + [(400, 88, 90)] * 9 + [(400, 88, 0), (1000, 340, 0)]
    es = _esforcos(specs)
    assert len(es) == 10
    assert {e.faixa for e in es} == {"d400"}
    assert all(e.pace_s_km == pytest.approx(220.0) for e in es)  # 88 / 400 x 1000
    assert all(e.duracao_s == 88 for e in es)
    assert sum(e.parada_apos_s for e in es) == 810  # 9 x 90 s


def test_1000_mais_500_juntados_entram_na_d1500():
    # 1000 m em 240 s + 500 m em 120,5 s: juntam (0,42% < 5%); bloco 1500 m, pace 360,5 / 1500 x 1000 = 240,3333.
    specs = [(2000, 660, 0), (1000, 240, 0), (500, 120.5, 120), (1000, 340, 0)]
    (e,) = _esforcos(specs)
    assert e.faixa == "d1500"
    assert (e.volta_inicial, e.volta_final) == (1, 2)
    assert e.distancia_m == 1500
    assert e.pace_s_km == pytest.approx(240.3333, abs=1e-4)


def test_esforco_entre_faixas_segue_a_adr():
    # 1350 m em 300 s (222,2 s/km <= 297) fica entre d1200 (ate 1260) e d1500 (a partir de 1425): sem faixa.
    (e,) = _esforcos([(1000, 340, 0), (1350, 300, 0), (1000, 340, 0)])
    assert e.faixa is None and e.distancia_m == 1350


def test_fc_do_esforco_e_ponderada_pela_duracao():
    # 1000 m em 240 s com FC 165 e 500 m em 121 s com FC 168 (juntam: 242 vs 240 s/km, +0,83%).
    # FC = (165 x 240 + 168 x 121) / 361 = (39600 + 20328) / 361 = 59928 / 361 = 166,0055
    specs = [(1000, 330, 0, 130), (1000, 240, 0, 165), (500, 121, 0, 168), (1000, 340, 0, 140)]
    (e,) = _esforcos(specs)
    assert e.faixa == "d1500"
    assert e.fc_media == pytest.approx(166.0055, abs=1e-4)


def test_sem_esforco_nao_ha_esforcos():
    assert _esforcos([(1000, 350, 0)] * 6) == ()


def test_so_blocos_de_esforco_entram():
    # aquecimento e desaquecimento de 1000 m (d1000) não entram: só o esforço de 400 m.
    es = _esforcos([(1000, 340, 0), (400, 88, 0), (1000, 340, 0)])
    assert [e.faixa for e in es] == ["d400"]


# --- Oráculo da #161 -----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _voltas_do_fit(nome):
    fit = ler_fit((PASTA_FIT / nome).read_bytes())
    return [
        VoltaTreino(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media, v.intensidade)
        for v in fit.voltas
    ]


NOMES_CORRIDA = [
    "esforcos_corrida_400_com_pausa.fit",
    "esforcos_corrida_1500_lap_automatico.fit",
    "esforcos_corrida_continuo_forte.fit",
    "esforcos_corrida_rodagem_leve.fit",
    "esforcos_corrida_misto.fit",
]


def _faixas(oraculo, nome):
    modalidade, ref, _ = oraculo.ESPERADO[nome]
    return [e.faixa for e in esforcos_corrida(montar_blocos(_voltas_do_fit(nome), modalidade, referencia=ref))]


@pytest.mark.parametrize("nome", NOMES_CORRIDA)
def test_esforcos_batem_com_o_oraculo(oraculo, nome):
    modalidade, ref, esperados = oraculo.ESPERADO[nome]
    es = esforcos_corrida(montar_blocos(_voltas_do_fit(nome), modalidade, referencia=ref))
    do_oraculo = [e for e in esperados if e.categoria == ESFORCO]
    assert len(es) == len(do_oraculo)
    for e, o in zip(es, do_oraculo):
        assert e.faixa == o.faixa, (nome, e)
        assert (e.volta_inicial, e.volta_final) == (o.volta_inicial, o.volta_final)
        assert e.distancia_m == pytest.approx(o.distancia_m, abs=0.01)
        assert e.pace_s_km == pytest.approx(o.intensidade, abs=1e-3)
        assert e.fc_media == pytest.approx(o.fc_media, abs=1e-6)


def test_contagem_por_faixa_nas_fixtures(oraculo):
    assert _faixas(oraculo, "esforcos_corrida_400_com_pausa.fit") == ["d400"] * 10
    assert _faixas(oraculo, "esforcos_corrida_1500_lap_automatico.fit") == ["d1500"] * 3
    assert _faixas(oraculo, "esforcos_corrida_continuo_forte.fit") == [None]  # 8000 m passa da d5000
    assert _faixas(oraculo, "esforcos_corrida_rodagem_leve.fit") == []
    misto = _faixas(oraculo, "esforcos_corrida_misto.fit")
    assert misto.count("d1000") == 5 and misto.count("d400") == 8 and len(misto) == 13
