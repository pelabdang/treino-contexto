"""Testes da série CTL/ATL/TSB (issue #139). Valores esperados calculados à mão (ADR 0010, exemplo 4)
e conferidos contra o oráculo da #137 (CARGA_DIA, SERIE e TOTAIS de test_carga_oraculo)."""

from datetime import date, timedelta

import pytest

from app.metricas.serie_carga import VERSAO, AtividadeCarga, calcular_serie

from .test_carga_oraculo import CARGA_DIA, ESPERADO, SEM_SAUDE, SERIE, TOTAIS, TOTAIS_SEM_SAUDE

D1 = date(2025, 1, 6)


def test_versao():
    assert VERSAO == "serie_carga@1"


def test_dia_unico():
    # k_ctl = 0,023528, k_atl = 0,133122: CTL = 100 x 0,023528, ATL = 100 x 0,133122
    s = calcular_serie([AtividadeCarga(D1, 100.0)])
    assert len(s.dias) == 1
    d = s.dias[0]
    assert d.ctl == pytest.approx(2.3528, abs=1e-4)
    assert d.atl == pytest.approx(13.3122, abs=1e-4)
    assert d.tsb == pytest.approx(-10.9594, abs=1e-4)
    assert d.aprendendo and (d.atividades, d.calculadas, d.sem_carga) == (1, 1, 0)


def test_sequencia_com_dia_sem_treino_exemplo_4_da_adr():
    s = calcular_serie([AtividadeCarga(D1, 100.0), AtividadeCarga(D1 + timedelta(days=2), 50.0)])
    assert [d.dia for d in s.dias] == [D1, D1 + timedelta(days=1), D1 + timedelta(days=2)]
    esperado = [(2.3528, 13.3122), (2.2975, 11.5401), (3.4198, 16.6599)]
    for d, (ctl, atl) in zip(s.dias, esperado):
        assert d.ctl == pytest.approx(ctl, abs=1e-4)
        assert d.atl == pytest.approx(atl, abs=1e-4)
    assert s.dias[2].tsb == pytest.approx(-13.2401, abs=1e-4)
    assert s.dias[1].carga == 0 and s.dias[1].atividades == 0


def test_dois_treinos_no_mesmo_dia_somam():
    # 60 + 40 no mesmo dia equivale a 100: L_d = 100
    a = calcular_serie([AtividadeCarga(D1, 60.0), AtividadeCarga(D1, 40.0)])
    b = calcular_serie([AtividadeCarga(D1, 100.0)])
    assert a.dias[0].carga == 100.0
    assert a.dias[0].ctl == pytest.approx(b.dias[0].ctl) and a.dias[0].atl == pytest.approx(b.dias[0].atl)
    assert (a.dias[0].atividades, a.dias[0].calculadas) == (2, 2)


def test_sem_carga_marca_o_dia_e_nao_entra_na_soma():
    s = calcular_serie([AtividadeCarga(D1, 100.0), AtividadeCarga(D1, motivo="sem_fc")])
    d = s.dias[0]
    assert (d.carga, d.atividades, d.calculadas, d.sem_carga) == (100.0, 2, 1, 1)
    assert s.totais.por_motivo["sem_fc"] == 1


def test_serie_termina_no_ultimo_dia_com_atividade_mesmo_sem_carga():
    s = calcular_serie([AtividadeCarga(D1, 100.0), AtividadeCarga(D1 + timedelta(days=3), motivo="sem_pace")])
    assert s.dias[-1].dia == D1 + timedelta(days=3)
    assert s.dias[-1].carga == 0 and s.dias[-1].sem_carga == 1


def test_comeca_no_primeiro_dia_com_carga_calculada():
    # sem_carga anterior fica fora da série, mas dentro dos totais
    s = calcular_serie([AtividadeCarga(D1 - timedelta(days=2), motivo="sem_limiar_na_data"), AtividadeCarga(D1, 10.0)])
    assert s.dias[0].dia == D1
    assert s.totais.sem_carga_total == 1 and s.totais.por_motivo["sem_limiar_na_data"] == 1


def test_aprendendo_vira_falso_no_dia_42():
    s = calcular_serie([AtividadeCarga(D1, 10.0), AtividadeCarga(D1 + timedelta(days=42), 10.0)])
    assert s.dias[41].aprendendo is True  # 41 dias desde o primeiro
    assert s.dias[42].aprendendo is False


def test_carga_constante_converge_para_o_valor():
    s = calcular_serie([AtividadeCarga(D1 + timedelta(days=i), 80.0) for i in range(300)])
    # no dia 42 (índice 41... com semente 0 e carga constante c): CTL_n = c x (1 - (1-k)^n) = c x (1 - e^(-n/42));
    # n = 42 (índice 41 é o 42o dia): 80 x (1 - e^-1) = 50,5696
    assert s.dias[41].ctl == pytest.approx(80 * (1 - 2.718281828459045**-1), abs=1e-3)
    assert s.dias[-1].ctl == pytest.approx(80.0, abs=0.1)
    assert s.dias[-1].atl == pytest.approx(80.0, abs=1e-6)


def test_sem_nenhuma_carga_serie_vazia_com_totais():
    s = calcular_serie([AtividadeCarga(D1, motivo="sem_dados_saude"), AtividadeCarga(D1, motivo="modalidade_sem_carga")], 2)
    assert s.dias == []
    assert (s.totais.calculadas, s.totais.sem_carga_total, s.totais.ignoradas_multiesporte) == (0, 2, 2)
    assert s.totais.por_motivo["sem_dados_saude"] == 1
    assert calcular_serie([]).dias == []


def test_validacao_da_entrada():
    with pytest.raises(ValueError):
        AtividadeCarga(D1)
    with pytest.raises(ValueError):
        AtividadeCarga(D1, motivo="inventado")
    with pytest.raises(ValueError):
        AtividadeCarga(D1, 10.0, "sem_fc")
    with pytest.raises(ValueError):
        AtividadeCarga(D1, -1.0)


def _atividades_do_oraculo():
    return [
        AtividadeCarga(e.dia, e.carga) if e.estado == "calculada" else AtividadeCarga(e.dia, motivo=e.motivo)
        for e in ESPERADO.values()
    ]


def test_bate_com_o_oraculo_da_137():
    s = calcular_serie(_atividades_do_oraculo(), TOTAIS["ignoradas_multiesporte"])
    por_dia = {d.dia: d for d in s.dias}
    assert len(s.dias) == 43 and s.dias[0].dia == date(2025, 3, 5) and s.dias[-1].dia == date(2025, 4, 16)
    for dia, valor in CARGA_DIA.items():
        assert por_dia[dia].carga == pytest.approx(valor, abs=1e-5)
    for dia, esp in SERIE.items():
        d = por_dia[dia]
        assert d.carga == pytest.approx(esp.carga, abs=1e-5)
        assert d.ctl == pytest.approx(esp.ctl, abs=1e-5)
        assert d.atl == pytest.approx(esp.atl, abs=1e-5)
        assert d.tsb == pytest.approx(esp.tsb, abs=1e-5)
        assert d.aprendendo is esp.aprendendo
        assert (d.atividades, d.calculadas, d.sem_carga) == (esp.atividades, esp.calculadas, esp.sem_carga)


def test_totais_batem_com_o_oraculo():
    t = calcular_serie(_atividades_do_oraculo(), TOTAIS["ignoradas_multiesporte"]).totais
    assert t.calculadas == TOTAIS["calculadas"]
    assert t.sem_carga_total == TOTAIS["sem_carga_total"]
    assert t.ignoradas_multiesporte == TOTAIS["ignoradas_multiesporte"]
    assert t.por_motivo == TOTAIS["por_motivo"]


def test_atleta_sem_saude_do_oraculo():
    atividades = [AtividadeCarga(ESPERADO[i].dia, motivo=m) for i, m in SEM_SAUDE.items()]
    s = calcular_serie(atividades, TOTAIS["ignoradas_multiesporte"])
    assert s.dias == []
    assert s.totais.calculadas == TOTAIS_SEM_SAUDE["calculadas"]
    assert s.totais.sem_carga_total == TOTAIS_SEM_SAUDE["sem_carga_total"]
    assert s.totais.por_motivo == TOTAIS_SEM_SAUDE["por_motivo"]
