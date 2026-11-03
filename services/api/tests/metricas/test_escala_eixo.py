"""Testes da escala mínima dos eixos (issue #63). Dados sintéticos, contas à mão.

Regra própria do projeto (ADR 0004); não há artigo.
"""

import pytest

from app.graficos.escala import (
    AMPLITUDE_MIN_FC_BPM,
    AMPLITUDE_MIN_PACE_S_KM,
    escala_eixo,
    escala_fc,
    escala_pace,
)
from app.metricas.tiros_1km import formatar_pace


def _valores(escala):
    return [m.valor for m in escala.marcas]


def test_constantes_decididas():
    assert AMPLITUDE_MIN_FC_BPM == 5  # decisão do Angelo
    assert AMPLITUDE_MIN_PACE_S_KM == 30


def test_fc_170_e_171_vira_faixa_de_5_centrada():
    # faixa dos dados = 1 < 5; centro = (170 + 171) / 2 = 170,5; 170,5 -+ 2,5 = 168 a 173
    e = escala_fc([170, 171])
    assert (e.min, e.max) == (168.0, 173.0)
    assert _valores(e) == [168, 169, 170, 171, 172, 173]
    assert len(e.marcas) >= 3
    assert [m.rotulo for m in e.marcas][:2] == ["168", "169"]


def test_fc_150_a_180_usa_a_faixa_dos_dados():
    # faixa = 30 >= 5. Passo 1 daria 31 marcas, x2 daria 16 (> 8); x5 dá 7: 150, 155, ..., 180
    e = escala_fc([150, 180])
    assert (e.min, e.max) == (150.0, 180.0)
    assert _valores(e) == [150, 155, 160, 165, 170, 175, 180]


def test_fc_faixa_exatamente_5_nao_amplia():
    e = escala_fc([168, 173])
    assert (e.min, e.max) == (168.0, 173.0)


def test_pace_240_e_242_vira_faixa_de_30():
    # centro = 241; 241 -+ 15 = 226 a 256; múltiplos de 10 dentro: 230, 240, 250 (3 marcas)
    e = escala_pace([240, 242])
    assert (e.min, e.max) == (226.0, 256.0)
    assert _valores(e) == [230, 240, 250]
    assert [m.rotulo for m in e.marcas] == ["3:50", "4:00", "4:10"]


def test_pace_faixa_minima_tem_4_marcas_quando_alinha():
    # centro 245; 230 a 260; múltiplos de 10: 230, 240, 250, 260 (4 marcas)
    e = escala_pace([245])
    assert (e.min, e.max) == (230.0, 260.0)
    assert _valores(e) == [230, 240, 250, 260]


@pytest.mark.parametrize("centro", [200 + 0.5 * i for i in range(200)])
def test_pace_faixa_minima_sempre_tem_ao_menos_3_marcas(centro):
    # faixa de 30 s/km e passo de 10: cabem 3 múltiplos (ou 4 se as pontas alinham)
    assert len(escala_pace([centro]).marcas) >= 3


def test_pace_rotulo_igual_a_formatar_pace():
    e = escala_pace([240, 300])
    assert _valores(e) == [240, 250, 260, 270, 280, 290, 300]  # faixa 60 >= 30: os dados, 7 marcas
    assert all(m.rotulo == formatar_pace(m.valor) for m in e.marcas)


def test_pace_faixa_larga_sobe_o_passo():
    # 190 a 320: passo 10 dá 14 marcas (> 8); x2 = 20: 200, 220, ..., 320 (7 marcas)
    e = escala_pace([190, 320])
    assert _valores(e) == [200, 220, 240, 260, 280, 300, 320]


def test_uma_sessao_so():
    # faixa 0; centro 170; 167,5 a 172,5; marcas 168..172
    e = escala_fc([170])
    assert (e.min, e.max) == (167.5, 172.5)
    assert _valores(e) == [168, 169, 170, 171, 172]


def test_centro_nao_inteiro_ainda_tem_marcas():
    # centro 171: 168,5 a 173,5; marcas 169..173 (passo 1 garante >= 3 marcas em 5 bpm)
    e = escala_fc([171])
    assert (e.min, e.max) == (168.5, 173.5)
    assert _valores(e) == [169, 170, 171, 172, 173]


@pytest.mark.parametrize("entrada", [[], [None], [None, None]])
def test_vazio_ou_so_none_devolve_none(entrada):
    assert escala_eixo(entrada, 5, 1) is None
    assert escala_fc(entrada) is None
    assert escala_pace(entrada) is None


def test_none_no_meio_e_ignorado():
    e = escala_fc([None, 170, None, 171])
    assert (e.min, e.max) == (168.0, 173.0)
