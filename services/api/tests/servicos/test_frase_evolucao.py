"""`frase_evolucao@1`: um teste por ramo e os exemplos a mao da nota docs/metricas/evolucao-series.md. Dados sinteticos; valores calculados a mao.

Calendario: HOJE = sexta 27/11/2026 -> ontem = 26/11. R = 30/10 a 26/11 (28 dias); A = 02/10 a 29/10.
Volume: domingo passado = 22/11; R = segunda 26/10 a 22/11 (4 semanas); A = 28/09 a 25/10.
"""

import re
from datetime import date, timedelta

import pytest
from app.servicos import frase_evolucao as fe
from app.servicos.frase_evolucao import Ponto, frase_evolucao

HOJE = date(2026, 11, 27)
ONTEM = HOJE - timedelta(days=1)
R_FIM, A_FIM = ONTEM, ONTEM - timedelta(days=28)  # 26/11 e 29/10


def _pts(valores, fim, passo=3):
    """Um treino a cada `passo` dias, do `fim` para tras."""
    return [Ponto(fim - timedelta(days=passo * i), v) for i, v in enumerate(valores)]


def _serie(r, a, **kw):
    return _pts(r, R_FIM, **kw) + _pts(a, A_FIM, **kw)


# ---------- exemplos a mao da nota ----------
def test_nota_pace_12s_mais_rapido():
    # R 342, 336, 348 -> mediana 342 (5:42); A 354, 348, 360 -> 354 (5:54); d = -12; L = 0,03 x 354 = 10,62; 12 >= 10,62
    f = frase_evolucao("pace_km", _serie([342, 336, 348], [354, 348, 360]), HOJE, titulo="Pace dos seus treinos leves")
    assert f.texto == ("Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), "
                       "12 s/km mais rápido que nas 4 semanas anteriores (5:54/km, 3 treinos).")
    assert (f.tipo, f.mudanca, f.a_favor, f.valor_atual, f.valor_anterior) == ("comparada", "menor", True, 342, 354)


def test_nota_pace_parecido():
    # A 348, 345, 351 -> 348; d = -6; L = 0,03 x 348 = 10,44; 6 < 10,44
    f = frase_evolucao("pace_km", _serie([342, 336, 348], [348, 345, 351]), HOJE)
    assert f.texto == "Pace nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), parecido com as 4 semanas anteriores (5:48/km, 3 treinos)."
    assert (f.mudanca, f.a_favor) == ("parecido", None)


def test_nota_fc_parecida():
    # R 148, 150, 152 -> 150; A 146, 148, 150 -> 148; d = 2 < 4 bpm
    f = frase_evolucao("fc", _serie([148, 150, 152], [146, 148, 150]), HOJE, titulo="Frequência cardíaca dos seus treinos leves")
    assert f.texto == ("Frequência cardíaca dos seus treinos leves nas últimas 4 semanas: 150 bpm (mediana de 3 treinos), "
                       "parecida com as 4 semanas anteriores (148 bpm, 3 treinos).")


def test_nota_volume_10km_a_menos():
    # R = 30, 36, 24, 30 (mediana 30); A = 40, 36, 44, 40 (mediana 40); d = -10; L = 4; 25%
    f = frase_evolucao("volume_km", _semanas([40, 36, 44, 40], [30, 36, 24, 30]), HOJE, titulo="Corrida")
    assert f.texto == "Corrida nas últimas 4 semanas: 30 km por semana (mediana), 10 km a menos (25%) que nas 4 semanas anteriores (40 km por semana)."
    assert (f.mudanca, f.a_favor, f.n_atual, f.n_anterior) == ("menor", False, 4, 4)


def test_eficiencia_nota_1_21_contra_1_17():
    # 10 000 m em 3 300 s com FC 150: (10 000 / 55) / 150 = 1,2121 -> 1,21; A 1,17; d = 0,04 >= L = 0,03 x 1,17 = 0,0351; 0,04 / 1,17 = 3,4% -> 3%
    f = frase_evolucao("eficiencia", _serie([1.21, 1.2121, 1.20], [1.17, 1.16, 1.18]), HOJE, titulo="Metros por batimento dos treinos leves")
    assert f.texto == ("Metros por batimento dos treinos leves nas últimas 4 semanas: 1,21 m/bat (mediana de 3 treinos), "
                       "3% mais que nas 4 semanas anteriores (1,17 m/bat, 3 treinos).")
    assert (f.mudanca, f.a_favor) == ("maior", True)


def _semanas(a, r, dia_da_semana=0):
    """`a` e `r`: 4 totais semanais (km), um treino por semana, na segunda (+dia_da_semana); A = semanas de 28/09, R = semanas de 26/10."""
    seg_a, seg_r = date(2026, 9, 28), date(2026, 10, 26)
    return ([Ponto(seg_a + timedelta(days=7 * i + dia_da_semana), v) for i, v in enumerate(a)]
            + [Ponto(seg_r + timedelta(days=7 * i + dia_da_semana), v) for i, v in enumerate(r)])


# ---------- por treino: ramos ----------
def test_sem_treino_em_r():
    f = frase_evolucao("pace_km", _pts([350, 350, 350], A_FIM), HOJE)
    assert (f.tipo, f.texto, f.mudanca, f.n_atual, f.n_anterior) == ("sem_treino", "Sem treinos desse tipo nas últimas 4 semanas.", None, 0, 3)


def test_sem_pontos_nenhum():
    assert frase_evolucao("fc", [], HOJE).tipo == "sem_treino"


def test_poucos_em_r():
    f = frase_evolucao("pace_km", _serie([342, 336], [354, 348, 360]), HOJE)
    assert (f.tipo, f.texto) == ("poucos", "Poucos treinos para comparar: 2 nas últimas 4 semanas, 3 nas 4 anteriores.")


def test_poucos_em_a():
    f = frase_evolucao("pace_km", _serie([342, 336, 348], [354]), HOJE)
    assert f.texto == "Poucos treinos para comparar: 3 nas últimas 4 semanas, 1 nas 4 anteriores."


def test_minimo_2_dos_tiros():
    pts = _serie([300, 310], [330, 320])
    assert frase_evolucao("pace_km", pts, HOJE).tipo == "poucos"
    f = frase_evolucao("pace_km", pts, HOJE, minimo=2)
    # R mediana 305, A mediana 325; d = -20; L = 9,75
    assert (f.tipo, f.valor_atual, f.valor_anterior) == ("comparada", 305, 325)
    assert "20 s/km mais rápido" in f.texto and "(mediana de 2 treinos)" in f.texto


def test_pace_mais_lento():
    # R 360, 366, 354 -> 360; A 342, 336, 348 -> 342; d = 18 >= 10,26
    f = frase_evolucao("pace_km", _serie([360, 366, 354], [342, 336, 348]), HOJE)
    assert "18 s/km mais lento que" in f.texto
    assert (f.mudanca, f.a_favor) == ("maior", False)


def test_limite_entra_como_diferenca():
    # A = 400 -> L = 12; d = 12 -> diferente; d = 11 -> parecido
    assert frase_evolucao("pace_km", _serie([388] * 3, [400] * 3), HOJE).mudanca == "menor"
    assert frase_evolucao("pace_km", _serie([389] * 3, [400] * 3), HOJE).mudanca == "parecido"


def test_fc_limite_4_bpm():
    assert frase_evolucao("fc", _serie([154] * 3, [150] * 3), HOJE).texto.count("4 bpm mais alta") == 1
    assert frase_evolucao("fc", _serie([153] * 3, [150] * 3), HOJE).mudanca == "parecido"


def test_fc_mais_baixa():
    f = frase_evolucao("fc", _serie([140, 141, 142], [150, 151, 149]), HOJE)
    assert "9 bpm mais baixa que" in f.texto and f.a_favor is True  # mediana 141 contra 150


def test_decide_sobre_o_valor_mostrado():
    # medianas de 2 valores: R (300, 301) = 300,5 -> mostra 301; A (313, 314) = 313,5 -> mostra 314; d mostrado = 13 (nao 13,0 por acaso); L = 0,03 x 314 = 9,42
    f = frase_evolucao("pace_km", _serie([300, 301], [313, 314]), HOJE, minimo=2)
    assert "5:01/km" in f.texto and "5:14/km" in f.texto and "13 s/km mais rápido" in f.texto


def test_pace_100m_e_velocidade():
    # natacao: R 105 (1:45), A 111 (1:51); d = -6; L = 3,33
    f = frase_evolucao("pace_100m", _serie([105] * 3, [111] * 3), HOJE, titulo="Ritmo médio com pausas")
    assert "1:45/100 m" in f.texto and "6 s/100 m mais rápido" in f.texto
    # velocidade: R 28,4; A 27,2; d = 1,2 >= 0,03 x 27,2 = 0,816
    v = frase_evolucao("velocidade", _serie([28.4] * 3, [27.2] * 3), HOJE)
    assert "28,4 km/h" in v.texto and "1,2 km/h mais rápida" in v.texto and v.a_favor is True


def test_so_as_janelas_entram():
    ruido = [Ponto(ONTEM + timedelta(days=1), 999), Ponto(A_FIM - timedelta(days=28), 1), Ponto(HOJE, 5)]  # hoje, e antes de A
    base = _serie([342, 336, 348], [354, 348, 360])
    assert frase_evolucao("pace_km", base + ruido, HOJE).texto == frase_evolucao("pace_km", base, HOJE).texto


def test_ontem_e_o_fim_de_r_e_28_dias_atras_o_de_a():
    pts = [Ponto(ONTEM, 342)] * 1 + [Ponto(ONTEM - timedelta(days=27), 336), Ponto(ONTEM - timedelta(days=13), 348)]  # 30/10 ainda e R
    pts += [Ponto(ONTEM - timedelta(days=28), 354), Ponto(ONTEM - timedelta(days=55), 348), Ponto(ONTEM - timedelta(days=40), 360)]  # 29/10 e 02/10 sao A
    f = frase_evolucao("pace_km", pts, HOJE)
    assert (f.n_atual, f.n_anterior) == (3, 3)


def test_ordem_e_varios_por_dia():
    pts = _serie([342, 336, 348], [354, 348, 360], passo=0)  # todos no mesmo dia
    f = frase_evolucao("pace_km", list(reversed(pts)), HOJE)
    assert (f.n_atual, f.n_anterior, f.valor_atual) == (3, 3, 342)


# ---------- aviso de treinos sem valor ----------
def test_aviso_um_sem_fc_de_cinco():
    # 1 de 5 em R = 20% -> avisa
    pts = _serie([148, 150, 152, 150], [146, 148, 150]) + [Ponto(R_FIM - timedelta(days=1), None)]
    f = frase_evolucao("fc", pts, HOJE)
    assert f.texto.endswith("1 dos 5 treinos ficou de fora porque não tem frequência cardíaca.") and f.n_atual == 4


def test_sem_aviso_abaixo_de_20_por_cento():
    # 1 de 6 = 16,7%
    pts = _serie([148, 150, 152, 150, 149], [146, 148, 150]) + [Ponto(R_FIM - timedelta(days=1), None)]
    assert "ficou de fora" not in frase_evolucao("fc", pts, HOJE).texto


def test_aviso_varios_e_nao_finitos():
    pts = _serie([148, 150, 152], [146, 148, 150]) + [Ponto(R_FIM - timedelta(days=1), None), Ponto(R_FIM - timedelta(days=2), float("nan"))]
    f = frase_evolucao("fc", pts, HOJE)
    assert f.texto.endswith("2 dos 5 treinos ficaram de fora porque não têm frequência cardíaca.")


def test_aviso_vem_tambem_com_poucos():
    pts = [Ponto(R_FIM, 150), Ponto(R_FIM - timedelta(days=1), None)]
    assert frase_evolucao("fc", pts, HOJE).texto.endswith("1 dos 2 treinos ficou de fora porque não tem frequência cardíaca.")


# ---------- volume ----------
def test_volume_parecido():
    # R 30, 32, 28, 30 -> 30; A 31, 30, 29, 30 -> 30
    f = frase_evolucao("volume_km", _semanas([31, 30, 29, 30], [30, 32, 28, 30]), HOJE)
    assert f.texto == "Volume nas últimas 4 semanas: 30 km por semana (mediana), parecido com as 4 semanas anteriores (30 km por semana)."


def test_volume_limite_10_por_cento():
    # A mediana 40 -> L = 4: d = 4 diferente (10%); d = 3 parecido
    assert "4 km a mais (10%)" in frase_evolucao("volume_km", _semanas([40] * 4, [44] * 4), HOJE).texto
    assert frase_evolucao("volume_km", _semanas([40] * 4, [43] * 4), HOJE).mudanca == "parecido"


def test_volume_soma_treinos_da_semana_e_semana_vazia_vale_zero():
    # R: semana 1 = 10 + 20 (30), semanas 2 e 3 vazias (0), semana 4 = 40 -> medianas de 30, 0, 0, 40 = 15; A: 20 x 4
    r = [Ponto(date(2026, 10, 26), 10), Ponto(date(2026, 10, 28), 20), Ponto(date(2026, 11, 20), 40)]
    a = [Ponto(date(2026, 9, 28) + timedelta(days=7 * i), 20) for i in range(4)]
    f = frase_evolucao("volume_km", r + a, HOJE)
    assert f.valor_atual == 15 and f.valor_anterior == 20 and f.n_atual == 3
    assert "15 km por semana (mediana), 5 km a menos (25%)" in f.texto  # d = -5; L = 2


def test_volume_semana_em_curso_fica_fora():
    # segunda 23/11 e 26/11 (semana em curso) nao entram; domingo 22/11 entra
    base = _semanas([40] * 4, [40] * 4, dia_da_semana=6)  # domingos: 04/10..25/10 e 01/11..22/11
    extra = [Ponto(date(2026, 11, 23), 500), Ponto(date(2026, 11, 26), 500)]
    assert frase_evolucao("volume_km", base + extra, HOJE).valor_atual == 40


def test_volume_no_proprio_domingo_a_semana_ainda_nao_acabou():
    # hoje = domingo 29/11: domingo passado = 22/11 (e nao 29/11)
    r = [Ponto(date(2026, 11, 29), 500)] + _semanas([40] * 4, [40] * 4)
    assert frase_evolucao("volume_km", r, date(2026, 11, 29)).valor_atual == 40


def test_volume_sem_percentual_com_base_pequena():
    # A mediana 2 km (< 3 km): sem percentual; R 4; d = 2 >= L = 0,2
    f = frase_evolucao("volume_km", _semanas([2] * 4, [4] * 4), HOJE)
    assert "2 km a mais que nas 4 semanas anteriores (2 km por semana)." in f.texto and "%" not in f.texto


def test_volume_horas_e_metros():
    h = frase_evolucao("volume_h", _semanas([3.5] * 4, [5.0] * 4), HOJE)  # d = 1,5; 43% (1,5 / 3,5 = 42,86)
    assert "5 h por semana (mediana), 1,5 h a mais (43%)" in h.texto and "(3,5 h por semana)" in h.texto
    m = frase_evolucao("volume_m", _semanas([3000] * 4, [2000] * 4), HOJE, titulo="Natação")
    assert "2000 m por semana (mediana), 1000 m a menos (33%)" in m.texto


def test_volume_sem_treino_e_poucos():
    assert frase_evolucao("volume_km", _semanas([40] * 4, []), HOJE).tipo == "sem_treino"
    assert frase_evolucao("volume_km", _semanas([], [30] * 4), HOJE).texto == "Poucos treinos para comparar: 4 nas últimas 4 semanas, 0 nas 4 anteriores."
    assert frase_evolucao("volume_km", _semanas([40] * 2, [30] * 2), HOJE, minimo=3).tipo == "poucos"


# ---------- condicionamento ----------
def _ctl(c, c28, maximo=None, ap=False, ap28=False):
    pts = [Ponto(ONTEM, c, aprendendo=ap), Ponto(ONTEM - timedelta(days=28), c28, aprendendo=ap28)]
    return pts + ([Ponto(date(2026, 9, 14), maximo)] if maximo is not None else [])


def test_ctl_estavel_com_maximo_da_nota():
    # nota: 42 contra 41; limiar = max(2, 0,05 x 41 = 2,05) = 2,05; d = 1 < 2,05; maximo 47 em 14/09
    f = frase_evolucao("ctl", _ctl(42, 41, 47), HOJE)
    assert f.texto == "Seu condicionamento está em 42, estável em relação a 4 semanas atrás (41). O maior valor do período foi 47, em 14/09."
    assert (f.tipo, f.mudanca, f.valor_atual, f.valor_anterior) == ("comparada", "parecido", 42, 41)


def test_ctl_subiu_e_caiu():
    # 50 contra 40: limiar 2; d = 10
    s = frase_evolucao("ctl", _ctl(50, 40), HOJE)
    assert s.texto.startswith("Seu condicionamento está em 50, acima do de 4 semanas atrás (40).") and s.a_favor is True
    c = frase_evolucao("ctl", _ctl(30, 40), HOJE)
    assert c.texto.startswith("Seu condicionamento está em 30, abaixo do de 4 semanas atrás (40).") and (c.mudanca, c.a_favor) == ("menor", False)


def test_ctl_limiar_5_por_cento_e_piso_2():
    # CTL28 = 100 -> limiar 5: d = 5 diferente, d = 4 parecido; CTL28 = 10 -> limiar 2: d = 2 diferente
    assert frase_evolucao("ctl", _ctl(105, 100), HOJE).mudanca == "maior"
    assert frase_evolucao("ctl", _ctl(104, 100), HOJE).mudanca == "parecido"
    assert frase_evolucao("ctl", _ctl(12, 10), HOJE).mudanca == "maior"
    assert frase_evolucao("ctl", _ctl(11, 10), HOJE).mudanca == "parecido"


def test_ctl_aprendendo_so_o_valor():
    for kw in ({"ap": True}, {"ap28": True}):
        f = frase_evolucao("ctl", _ctl(42, 20, **kw), HOJE)
        assert f.tipo == "so_valor" and f.mudanca is None and f.texto.startswith("Seu condicionamento está em 42. O maior valor")


def test_ctl_sem_ponto_de_28_dias_so_o_valor_e_sem_ontem_sem_dado():
    assert frase_evolucao("ctl", [Ponto(ONTEM, 42.4)], HOJE).texto == "Seu condicionamento está em 42. O maior valor do período foi 42, em 26/11."
    assert frase_evolucao("ctl", [Ponto(HOJE, 42)], HOJE).tipo == "sem_dado"
    assert frase_evolucao("ctl", [], HOJE).texto == "Sem condicionamento calculado até ontem."


def test_ctl_maximo_ignora_dias_aprendendo_e_empata_no_primeiro():
    pts = _ctl(42, 41) + [Ponto(date(2026, 8, 1), 90, aprendendo=True), Ponto(date(2026, 9, 14), 47), Ponto(date(2026, 10, 3), 47)]
    assert frase_evolucao("ctl", pts, HOJE).texto.endswith("O maior valor do período foi 47, em 14/09.")


# ---------- textos ----------
def test_tipo_desconhecido():
    with pytest.raises(ValueError):
        frase_evolucao("potencia", [], HOJE)


def test_versao_e_texto_sem_sigla_nem_conselho():
    casos = [frase_evolucao("pace_km", _serie([342, 336, 348], [354, 348, 360]), HOJE), frase_evolucao("fc", [], HOJE),
             frase_evolucao("volume_km", _semanas([40] * 4, [30] * 4), HOJE), frase_evolucao("ctl", _ctl(50, 40, 55), HOJE)]
    proibidas = r"\b(CTL|ATL|TSB|MAD|melhor|melhorou|piorou|pior|bom|boa|ruim|risco|lesão|cuidado|deve|evite|recomend\w*|descanse|alarm\w*)\b"
    for f in casos:
        assert f.versao == fe.VERSAO == "frase_evolucao@1"
        assert not re.search(proibidas, f.texto, re.IGNORECASE), f.texto
