"""Oráculo da série de tiros de 1 km com as fixtures sintéticas (issue #30).

Lê as tabelas VOLTAS_A..D de ``tests/fixtures/garmin/gerar_fixtures.py`` (não
depende do zip nem do parser). ``ESPERADO`` guarda os valores calculados à mão,
para a #14 (série no banco) e a #18 (QA) reutilizarem.

Regra (roteiro, Meta 1; nota docs/metricas/tiros-1km.md; sem artigo, regra própria):
  pace (s/km) = soma(duração dos tiros) / soma(distância dos tiros) x 1000
  FC (bpm)    = soma(FC x duração) / soma(duração)

Conta à mão, 1000000001 (6 x 1 km; tiros = voltas "active"):
  durações 255+252+250+251+249+248 = 1505 s; distância 6 x 1000 = 6000 m
  pace = 1505 / 6000 x 1000 = 250,8333 s/km (4:10,8)
  FC x duração: 42075 + 42336 + 42500 + 42921 + 43077 + 43400 = 256309
  FC = 256309 / 1505 = 170,3050 bpm
Conta à mão, 1000000002 (5 x 1 km):
  durações 240+238+237+236+234 = 1185 s; distância 5000 m
  pace = 1185 / 5000 x 1000 = 237,0 s/km (3:57,0)
  FC x duração: 39840 + 40460 + 40764 + 41064 + 41418 = 203546
  FC = 203546 / 1185 = 171,7688 bpm
Melhor tiro (#151): o de menor pace, com a FC dele.
  1000000001: paces 255, 252, 250, 251, 249, 248 s/km -> melhor 248,0 s/km (4:08), FC 175 (6o tiro)
  1000000002: paces 240, 238, 237, 236, 234 s/km -> melhor 234,0 s/km (3:54), FC 177 (5o tiro)
  (cada tiro tem 1000 m, então pace = duração em s/km)
Fora da série: 1000000003 (8 x 1 km leve, sem tiros: nenhuma volta é 8% mais
rápida que a mediana), 1000000004 (natação) e 1000000005 (esteira sem FIT, sem voltas).
"""

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

from app.metricas.tiros_1km import (
    SessaoTiros,
    para_apresentacao,
    serie_por_sessao,
    tiro_de_bloco,
    tiros_de_blocos,
)

GERADOR = Path(__file__).parents[4] / "tests" / "fixtures" / "garmin" / "gerar_fixtures.py"

# id da atividade -> (n_tiros, pace s/km, FC bpm), à mão (ver docstring)
# id -> (melhor pace s/km, FC do melhor tiro bpm), à mão (ver docstring)
MELHOR_TIRO = {1000000001: (248.0, 175), 1000000002: (234.0, 177)}
ESPERADO = {
    1000000001: (6, 1505 / 6000 * 1000, 256309 / 1505),
    1000000002: (5, 1185 / 5000 * 1000, 203546 / 1185),
}
FORA_DA_SERIE = (1000000003, 1000000004, 1000000005)


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sessoes(gerador):
    """Sessões das fixtures pela visão de esforços (@5): voltas -> blocos (esforcos@1, ritmo habitual de 330 s/km)."""
    ajuda = importlib.util.spec_from_file_location("_tiros_blocos", Path(__file__).with_name("_tiros_blocos.py"))
    mod = importlib.util.module_from_spec(ajuda)
    ajuda.loader.exec_module(mod)
    sessoes = []
    for i, a in enumerate(gerador.ATIVIDADES):
        if a.voltas is None or a.sport_type != "RUNNING":  # sem FIT: nada a detectar; natação não tem tiros
            continue
        blocos = mod.blocos_de([(dist, dur, 0.0, fc) for (_, dist, dur, fc) in a.voltas])
        r = tiros_de_blocos(blocos)
        por_ordem = {b.ordem: b for b in blocos}
        # data só para ordenar a série; a data local real é da #14
        sessoes.append(SessaoTiros(a.id, date(2025, 3, 1 + i), r.eh_intervalado,
                                   tuple(tiro_de_bloco(por_ordem[o]) for o in r.tiros), r.versao))
    return sessoes


def test_serie_das_fixtures_bate_com_o_calculo_a_mao(gerador):
    serie = serie_por_sessao(_sessoes(gerador))
    assert [p.atividade_id for p in serie] == list(ESPERADO)
    for p in serie:
        n, pace, fc = ESPERADO[p.atividade_id]
        assert p.n_tiros == n
        assert p.pace_s_km == pytest.approx(pace, abs=1e-9)
        assert p.fc_media == pytest.approx(fc, abs=1e-9)
        assert p.versao == "tiros_1km@5"


def test_melhor_tiro_das_fixtures_bate_com_o_calculo_a_mao(gerador):
    for p in serie_por_sessao(_sessoes(gerador)):
        pace, fc = MELHOR_TIRO[p.atividade_id]
        assert p.melhor_pace_s_km == pytest.approx(pace, abs=1e-9)
        assert p.melhor_fc_media == fc


def test_valores_a_mao_apresentados(gerador):
    # 250,8333 -> 250,8 ; 170,3050 -> 170,3 ; 237,0 ; 171,7688 -> 171,8
    a, b = serie_por_sessao(_sessoes(gerador))
    assert (para_apresentacao(a.pace_s_km), para_apresentacao(a.fc_media)) == (250.8, 170.3)
    assert (para_apresentacao(b.pace_s_km), para_apresentacao(b.fc_media)) == (237.0, 171.8)


def test_atividades_fora_da_serie(gerador):
    ids_na_serie = {p.atividade_id for p in serie_por_sessao(_sessoes(gerador))}
    assert not ids_na_serie & set(FORA_DA_SERIE)
