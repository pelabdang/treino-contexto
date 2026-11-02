"""Ritmo habitual do atleta e filtro da série (issue #53, tiros_1km@3). Valores à mão.

Regra (docs/metricas/tiros-1km.md): ritmo habitual = mediana do pace (duração / distância x 1000)
das corridas de mais de 3 km, sem esteira, com data anterior à da sessão, nos 84 dias antes dela;
com menos de 10 na janela, todo o histórico anterior; sem histórico, None (não filtra).
Os tiros valem se pace_tiros <= habitual x 0,95.
Fonte: regra própria do projeto (não há artigo); a mediana é a estatística robusta usual.
"""

from datetime import date, timedelta

import pytest

from app.metricas.tiros_1km import (
    CorridaHistorico,
    mais_rapido_que_o_habitual,
    pace_habitual,
)

HOJE = date(2025, 6, 1)


def corrida(dias_antes, pace, km=8.0, esteira=False):
    """Corrida `dias_antes` de HOJE, com `km` e pace s/km (duração = pace x km)."""
    return CorridaHistorico(HOJE - timedelta(days=dias_antes), km * 1000, pace * km, esteira)


def test_sem_historico_devolve_none():
    assert pace_habitual([], HOJE) is None
    # só corridas posteriores ou do mesmo dia: não são histórico
    assert pace_habitual([corrida(0, 330), corrida(-3, 330)], HOJE) is None


def test_mediana_do_historico_com_menos_de_10_corridas_na_janela():
    # 3 corridas anteriores, a 300, 330 e 360 s/km: mediana 330.
    h = [corrida(5, 300), corrida(10, 330), corrida(15, 360)]
    assert pace_habitual(h, HOJE) == pytest.approx(330.0)


def test_menos_de_10_na_janela_usa_o_historico_todo():
    # 4 corridas na janela (a 330) e 4 antes dela (a 400, há mais de 84 dias):
    # < 10 na janela, então usa as 8: ordenadas 330 x4, 400 x4, mediana = (330 + 400) / 2 = 365.
    h = [corrida(d, 330) for d in (5, 10, 20, 30)] + [corrida(d, 400) for d in (100, 120, 150, 200)]
    assert pace_habitual(h, HOJE) == pytest.approx(365.0)


def test_com_10_ou_mais_na_janela_so_a_janela_conta():
    # 10 corridas na janela a 330 e 5 muito antigas a 420: só as 10 contam.
    h = [corrida(d, 330) for d in range(5, 55, 5)] + [corrida(d, 420) for d in (100, 150, 200, 250, 300)]
    assert len([c for c in h if c.data >= HOJE - timedelta(days=84)]) == 10
    assert pace_habitual(h, HOJE) == pytest.approx(330.0)


def test_limite_da_janela_de_84_dias():
    # 10 corridas na janela: uma exatamente 84 dias antes ainda conta (janela inclusiva);
    # outra 85 dias antes não conta (11a e 12a corridas a 500 s/km mudariam a mediana).
    dentro = [corrida(d, 330) for d in (1, 2, 3, 4, 5, 6, 7, 8, 9)] + [corrida(84, 330)]
    fora = [corrida(85, 500)] * 3
    assert pace_habitual(dentro + fora, HOJE) == pytest.approx(330.0)


def test_corridas_de_ate_3_km_e_de_esteira_nao_entram():
    # exatamente 3 km (3000 m) não entra (precisa ser mais de 3 km); esteira não entra.
    h = [corrida(5, 330), corrida(10, 200, km=3.0), corrida(15, 200, esteira=True)]
    assert pace_habitual(h, HOJE) == pytest.approx(330.0)
    # 3,001 km entra
    h2 = [corrida(5, 330), CorridaHistorico(HOJE - timedelta(days=10), 3001.0, 3001 * 0.2)]
    assert pace_habitual(h2, HOJE) == pytest.approx((330 + 200) / 2)


def test_so_corridas_que_nao_servem_devolve_none():
    assert pace_habitual([corrida(5, 330, km=3.0), corrida(6, 330, esteira=True)], HOJE) is None


def test_filtro_sem_habitual_nao_filtra():
    assert mais_rapido_que_o_habitual(500.0, None) is True


def test_limite_exato_entra():
    # habitual 300 s/km: limite = 300 x 0,95 = 285. 285 entra (<=); 285,01 não.
    assert mais_rapido_que_o_habitual(285.0, 300.0) is True
    assert mais_rapido_que_o_habitual(285.01, 300.0) is False


def test_rodagem_com_paradas_curtas_fica_fora_e_tiros_reais_ficam_dentro():
    # habitual 330 s/km (5:30). Limite = 313,5.
    # Rodagem com paradas: "tiros" a 335 s/km (> 313,5): fora.
    assert mais_rapido_que_o_habitual(335.0, 330.0) is False
    # Tiros de verdade a 270 s/km: dentro.
    assert mais_rapido_que_o_habitual(270.0, 330.0) is True
