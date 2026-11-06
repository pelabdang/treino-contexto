"""Treino-chave contínuo (issue #165; ADR 0008, item 6; nota docs/metricas/esforcos.md).

Dado sintético, valores esperados à mão. Regra própria do projeto, sem artigo (aprovada pelo Angelo em 04/11).
Limiar de esforço: corrida pace <= ref x 0,90 (ref 330 -> 297 s/km); ciclismo velocidade >= ref x 1,15.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.metricas.esforcos import VoltaTreino, montar_blocos, treino_chave_continuo

RAIZ = Path(__file__).parents[4]
ORACULO = Path(__file__).with_name("test_esforcos_oraculo.py")
PASTA_FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"


def _voltas(specs):
    """specs: (distancia_m, duracao_s, parada_apos_s)."""
    voltas, t = [], 0.0
    for i, (dist, dur, parada) in enumerate(specs):
        voltas.append(VoltaTreino(i, t, dur, dist))
        t += dur + parada
    return voltas


def _chave(specs, modalidade="corrida", ref=330):
    return treino_chave_continuo(montar_blocos(_voltas(specs), modalidade, referencia=ref), modalidade)


def test_8km_a_270_com_habitual_330_e_treino_chave():
    # 8 x 1000 m em 270 s: 2160 s >= 1200; pace 270 <= 297; margem 1 - 270/330 = 0,1818.
    r = _chave([(1000, 270, 0)] * 8)
    assert r.treino_chave and r.motivo == "continuo"
    assert r.duracao_s == 2160 and r.distancia_m == 8000 and r.pace_s_km == 270
    assert r.margem == pytest.approx(0.1818, abs=1e-4)
    assert r.esforcos_fora == 0 and r.ref_origem == "habitual"


def test_rodagem_a_330_nao_e_treino_chave():
    # 330 > 297: nenhum esforço, tudo leve.
    r = _chave([(1000, 330, 0)] * 8)
    assert not r.treino_chave and r.motivo == "sem_esforco" and r.duracao_s == 0


def test_limite_exato_de_ritmo_entra():
    # 297 s/km é exatamente 330 x 0,90: 5000 m em 1485 s (1485 / 5000 x 1000 = 297). Entra; 297,2 não.
    assert _chave([(5000, 1485, 0)]).treino_chave
    assert not _chave([(5000, 1486, 0)]).treino_chave  # 297,2 s/km


def test_limite_exato_de_duracao_entra():
    # 4800 m em 1200 s = 250 s/km, 20 min exatos: entra; 1199 s não (motivo "curto").
    assert _chave([(4800, 1200, 0)]).treino_chave
    r = _chave([(4796, 1199, 0)])
    assert not r.treino_chave and r.motivo == "curto" and r.duracao_s == 1199


def test_uma_repeticao_fora_ainda_passa_e_duas_nao():
    # 8 km a 270 s/km (2160 s) + recuperação lenta (400 m em 168 s = 420 s/km) + 400 m em 88 s (220 s/km):
    # 1 esforço fora da sequência (< 2): passa.
    base = [(1000, 270, 0)] * 8 + [(400, 168, 0), (400, 88, 0)]
    r = _chave(base)
    assert r.treino_chave and r.esforcos_fora == 1
    # mais uma recuperação e outro 400 m forte: 2 fora, é treino de repetição.
    r2 = _chave(base + [(400, 168, 0), (400, 88, 0)])
    assert not r2.treino_chave and r2.motivo == "repeticoes" and r2.esforcos_fora == 2


def test_parada_longa_corta_a_sequencia():
    # 5 x 1000 m em 240 s (240 s/km <= 297) com 90 s parados: somam 1200 s, mas 90 s >= 15 s é recuperação.
    # Cada sequência tem 240 s: curto.
    r = _chave([(1000, 240, 90)] * 4 + [(1000, 240, 0)])
    assert not r.treino_chave and r.motivo == "curto" and r.duracao_s == 240 and r.esforcos_fora == 4


def test_parada_de_14_s_nao_corta_mas_15_s_corta():
    # 1000 m a 240 s e 1000 m a 290 s: diferem 20% (> 5%), logo dois blocos de esforço. Com 14 s parados a
    # sequência segue (240 + 290 = 530 s); com 15 s corta.
    specs = [(1000, 240, 14), (1000, 290, 0)]
    assert _chave(specs).duracao_s == 530
    assert _chave([(1000, 240, 15), (1000, 290, 0)]).duracao_s == 290  # maior sequência: 290 s


def test_progressivo_forte_sem_recuperacao_e_uma_sequencia():
    # 4 x 1000 m a 296 s/km e 4 x 1000 m a 270 s/km: 296 -> 270 é -8,8%, dois blocos esforço vizinhos, sem parada.
    # 4 x 296 + 4 x 270 = 2264 s.
    r = _chave([(1000, 296, 0)] * 4 + [(1000, 270, 0)] * 4)
    assert r.treino_chave and r.duracao_s == 2264 and r.esforcos_fora == 0
    assert (r.sequencia_bloco_inicial, r.sequencia_bloco_final) == (0, 1)


def test_ciclismo_20_min_a_24_com_habitual_20_e_treino_chave():
    # limiar 20 x 1,15 = 23. 8000 m em 1200 s = 24 km/h, 20 min exatos; margem 24/20 - 1 = 0,20.
    r = _chave([(5000, 750, 0), (3000, 450, 0)], "ciclismo", ref=20)
    assert r.treino_chave and r.duracao_s == 1200 and r.velocidade_kmh == pytest.approx(24.0)
    assert r.margem == pytest.approx(0.20)


def test_ciclismo_limiar_de_15_por_cento_e_nao_10():
    # 23 km/h é exatamente 20 x 1,15 (entra): 7666,67 m em 1200 s. 22,5 km/h (+12,5%) não entra no ciclismo.
    assert _chave([(7666.67, 1200, 0)], "ciclismo", ref=20).treino_chave
    assert not _chave([(7500, 1200, 0)], "ciclismo", ref=20).treino_chave


def test_ciclismo_5_x_4_min_e_repeticao_nao_continuo():
    specs = [(6250, 900, 0)]
    for _ in range(5):
        specs += [(2400, 240, 0), (733.33, 120, 0)]
    r = _chave(specs, "ciclismo", ref=22)
    assert not r.treino_chave and r.motivo == "curto" and r.duracao_s == 240


def test_sem_historico_o_resultado_avisa_a_origem():
    # um bloco só: a mediana da atividade é ele mesmo, nunca passa do limiar (limitação da ADR).
    r = treino_chave_continuo(montar_blocos(_voltas([(1000, 270, 0)] * 8), "corrida"), "corrida")
    assert not r.treino_chave and r.ref_origem == "atividade"


def test_modalidade_sem_suporte_nao_e_treino_chave():
    r = treino_chave_continuo(montar_blocos(_voltas([(1000, 270, 0)] * 8), "natacao"), "natacao")
    assert not r.treino_chave and r.motivo == "sem_esforco"


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("nome", list(range(7)))
def test_bate_com_o_oraculo_da_161(oraculo, nome):
    nome = list(oraculo.ESPERADO)[nome]
    modalidade, ref, esperados = oraculo.ESPERADO[nome]
    fit = ler_fit((PASTA_FIT / nome).read_bytes())
    voltas = [
        VoltaTreino(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media, v.intensidade)
        for v in fit.voltas
    ]
    r = treino_chave_continuo(montar_blocos(voltas, modalidade, referencia=ref), modalidade)
    assert r.treino_chave == any(b.treino_chave for b in esperados), nome
