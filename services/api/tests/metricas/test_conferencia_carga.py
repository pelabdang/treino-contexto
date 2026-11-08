"""Testes da conferência com a carga do Garmin (issue #144; ADR 0010, item 8). Valores calculados à mão.

Séries inventadas, com relação conhecida com a nossa. Testam o código da conferência, não a fisiologia.
"""

from datetime import date, timedelta

import pytest

from app.metricas.conferencia_carga import DiaGarmin, VERSAO, conferir, razao_nossa, spearman
from app.metricas.serie_carga import DiaCarga

D0 = date(2025, 3, 1)


def dia(i, ctl=10.0, atl=10.0, sem_carga=0):
    return DiaCarga(D0 + timedelta(days=i), 0.0, ctl, atl, ctl - atl, False, sem_carga, 0, sem_carga)


def gar(i, aguda=None, cronica=None, razao=None):
    return DiaGarmin(D0 + timedelta(days=i), aguda, cronica, razao)


def test_versao():
    assert VERSAO == "conferencia_carga@1"


def test_spearman_a_mao_sem_empates():
    # x = 1..5, y = 2,1,4,3,5: d = -1,1,-1,1,0, soma d^2 = 4, rho = 1 - 6 x 4 / (5 x 24) = 0,8
    assert spearman([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]) == pytest.approx(0.8)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_com_empate_usa_posto_medio():
    # x = 1,2,3,4 (postos 1,2,3,4); y = 1,1,2,3 (postos 1,5; 1,5; 3; 4). Os dois postos têm média 2,5.
    # desvios de x: -1,5 -0,5 0,5 1,5 (soma de quadrados 5); desvios de y: -1 -1 0,5 1,5 (soma de quadrados 4,5)
    # soma dos produtos = 1,5 + 0,5 + 0,25 + 2,25 = 4,5; rho = 4,5 / raiz(5 x 4,5) = 0,9487
    assert spearman([1, 2, 3, 4], [1, 1, 2, 3]) == pytest.approx(4.5 / (5 * 4.5) ** 0.5)


def test_spearman_indefinido():
    assert spearman([1, 2], [1, 2]) is None  # menos de 3 pares
    assert spearman([1, 2, 3], [5, 5, 5]) is None  # série constante
    with pytest.raises(ValueError):
        spearman([1, 2, 3], [1, 2])


ATL = [3, 1, 4, 1.5, 5, 9, 2, 6, 5.5, 3.5]  # sem empates


def test_relacao_monotona_da_rho_1_nos_niveis_e_nas_diferencas():
    nossa = [dia(i, ctl=a, atl=a) for i, a in enumerate(ATL)]
    garmin = [gar(i, aguda=10 * a, cronica=2 * a) for i, a in enumerate(ATL)]
    c = conferir(nossa, garmin)
    assert c.cobertura == (c.cobertura.__class__(10, 10, 10, 0, 10))
    m = c.medida("niveis", "atl_aguda")
    assert (m.n, m.spearman) == (10, pytest.approx(1.0))
    assert c.medida("niveis", "ctl_cronica").spearman == pytest.approx(1.0)
    # y = 10 x: as diferenças são 10 x as de x, mesmo posto: 9 pares, rho = 1
    d = c.medida("diferencas", "atl_aguda")
    assert (d.n, d.spearman) == (9, pytest.approx(1.0))


def test_defasagem_o_garmin_atrasado_2_dias_acha_o_pico_em_k_2():
    # Garmin no dia d+2 = 10 x nossa no dia d. Garmin existe de 2 a 11; nossa de 0 a 9.
    nossa = [dia(i, atl=a) for i, a in enumerate(ATL)]
    garmin = [gar(i + 2, aguda=10 * a) for i, a in enumerate(ATL)]
    c = conferir(nossa, garmin)
    k2 = c.medida("defasagem", "atl_aguda", 2)
    assert (k2.n, k2.spearman) == (10, pytest.approx(1.0))
    # k = 0: pares nos dias 2..9, nossa ATL[2:10] contra Garmin = 10 x ATL[0:8]
    k0 = c.medida("defasagem", "atl_aguda", 0)
    assert k0.n == 8
    esperado = spearman(ATL[2:10], ATL[0:8])
    assert k0.spearman == pytest.approx(esperado) and k0.spearman < 1.0
    assert c.medida("niveis", "atl_aguda").n == 8  # mesmos pares do k = 0
    assert [m.defasagem for m in c.medidas if m.grupo == "defasagem" and m.comparacao == "atl_aguda"] == list(range(-3, 4))


def test_defasagem_negativa():
    # Garmin à frente: Garmin em d-1 = 10 x nossa em d. k = -1
    nossa = [dia(i, atl=a) for i, a in enumerate(ATL)]
    garmin = [gar(i - 1, aguda=10 * a) for i, a in enumerate(ATL)]
    m = conferir(nossa, garmin).medida("defasagem", "atl_aguda", -1)
    assert (m.n, m.spearman) == (10, pytest.approx(1.0))


def test_dia_com_atividade_sem_carga_e_descartado_e_contado():
    nossa = [dia(i, atl=a, sem_carga=1 if i == 4 else 0) for i, a in enumerate(ATL)]
    garmin = [gar(i, aguda=a) for i, a in enumerate(ATL)]
    c = conferir(nossa, garmin)
    assert (c.cobertura.dias_em_comum, c.cobertura.descartados_sem_carga, c.cobertura.dias_comparados) == (10, 1, 9)
    assert c.medida("niveis", "atl_aguda").n == 9
    # diferenças: o dia 4 fora tira os pares (3,4) e (4,5): 9 - 2 = 7 (dias 1,2,3 e 6,7,8,9 -> 2+... )
    assert c.medida("diferencas", "atl_aguda").n == 7
    # sem descartar, os 10 dias entram
    t = conferir(nossa, garmin, descartar_sem_carga=False)
    assert t.cobertura.dias_comparados == 10 and t.medida("niveis", "atl_aguda").n == 10
    assert t.medida("diferencas", "atl_aguda").n == 9


def test_dias_so_de_uma_serie_nao_entram_mas_contam_na_cobertura():
    nossa = [dia(i, atl=a) for i, a in enumerate(ATL[:6])]  # 0..5
    garmin = [gar(i, aguda=a) for i, a in enumerate(ATL[3:], start=3)]  # 3..9
    c = conferir(nossa, garmin)
    assert (c.cobertura.dias_nossa, c.cobertura.dias_garmin, c.cobertura.dias_em_comum, c.cobertura.dias_comparados) == (
        6, 7, 3, 3)
    assert c.medida("niveis", "atl_aguda").n == 3


def test_razao_nossa_contra_a_do_garmin():
    # ATL/CTL: 6/3 = 2, 4/4 = 1, 9/3 = 3, 5/10 = 0,5. O Garmin traz 2 x razão: mesmo posto, rho = 1.
    pares = [(6, 3), (4, 4), (9, 3), (5, 10)]
    nossa = [dia(i, ctl=c, atl=a) for i, (a, c) in enumerate(pares)]
    garmin = [gar(i, razao=2 * a / c) for i, (a, c) in enumerate(pares)]
    m = conferir(nossa, garmin).medida("razao", "razao")
    assert (m.n, m.spearman) == (4, pytest.approx(1.0))
    assert razao_nossa(dia(0, ctl=0.0, atl=5.0)) is None
    assert razao_nossa(dia(0, ctl=4.0, atl=6.0)) == pytest.approx(1.5)


def test_ctl_zero_nao_entra_na_razao_e_campo_ausente_no_garmin_nao_entra():
    nossa = [dia(0, ctl=0.0, atl=0.0), dia(1, ctl=2.0, atl=4.0), dia(2, ctl=5.0, atl=5.0), dia(3, ctl=4.0, atl=2.0)]
    garmin = [gar(0, aguda=1, razao=1.0), gar(1, aguda=None, razao=2.0), gar(2, aguda=3, razao=1.0), gar(3, aguda=4, razao=0.5)]
    c = conferir(nossa, garmin)
    assert c.medida("razao", "razao").n == 3  # sem o dia 0 (CTL = 0)
    assert c.medida("niveis", "atl_aguda").n == 3  # sem o dia 1 (aguda ausente)


def test_serie_do_garmin_vazia_nao_quebra():
    c = conferir([dia(i) for i in range(5)], [])
    assert c.cobertura.dias_comparados == 0
    assert all(m.n == 0 and m.spearman is None for m in c.medidas)
