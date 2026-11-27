"""`frase_forma@1` e a serie ate ontem (`serie_carga@2`): casos a mao do Caio, regras na ordem, textos sem sigla e sem conselho. Dados sinteticos."""

import re
from datetime import date, datetime, timedelta, timezone

import pytest
from app.metricas import serie_carga as sc
from app.servicos import frase_forma as ff
from app.servicos.carga_leitura import hoje_do_atleta
from app.servicos.carga_textos import aprendendo_texto

D0 = date(2026, 1, 1)


def _dia(i, ctl, atl, aprendendo=False, calculadas=1, sem_carga=0, avisavel=None):
    return sc.DiaCarga(dia=D0 + timedelta(days=i), carga=10.0, ctl=ctl, atl=atl, tsb=ctl - atl, aprendendo=aprendendo, atividades=calculadas + sem_carga,
                       calculadas=calculadas, sem_carga=sem_carga, sem_carga_avisavel=sem_carga if avisavel is None else avisavel)


def _serie(c14, c, f, n=60, **ult):
    """`n` dias; o primeiro dia do grafico (n-14) tem CTL `c14` e o ultimo tem CTL `c` e ATL `f`; os 42 primeiros dias aprendem."""
    dias = []
    for i in range(n):
        aprend = i < sc.DIAS_APRENDENDO
        ctl, atl = (c14, c14) if i == n - 14 else (c, f) if i == n - 1 else (c14, c14)
        dias.append(_dia(i, ctl, atl, aprendendo=aprend, **(ult if i == n - 1 else {})))
    return sc.SerieCarga(sc.VERSAO, dias, sc.TotaisCarga(n, 0, {m: 0 for m in sc.MOTIVOS}, 0))


# ---------- os casos a mao do Caio ----------

@pytest.mark.parametrize("f,esperado", [(52, "parecidos"), (60, "acima"), (80, "bem_acima"), (30, "bem_abaixo"), (44, "abaixo")])
def test_faixa_com_condicionamento_50(f, esperado):
    assert ff.faixa(f, 50) == esperado


@pytest.mark.parametrize("c14,c,esperado", [(40, 42, "subiu"), (40, 41, "perto"), (100, 104, "perto"), (100, 105, "subiu"), (40, 38, "caiu"), (100, 95, "caiu")])
def test_tendencia(c14, c, esperado):
    assert ff.tendencia(c14, c) == esperado


def test_bordas_da_faixa():
    assert ff.faixa(55, 50) == "parecidos" and ff.faixa(56, 50) == "acima"  # lim = 5 em C = 50
    assert ff.faixa(7, 5) == "parecidos" and ff.faixa(8, 5) == "acima"  # lim minimo de 2 pontos; C < 10: nunca "bem"
    assert ff.faixa(14, 9) == "acima" and ff.faixa(15, 10) == "bem_acima" and ff.faixa(2, 9) == "abaixo" and ff.faixa(6, 10) == "bem_abaixo"
    assert ff.faixa(75, 50) == "bem_acima" and ff.faixa(74, 50) == "acima" and ff.faixa(34, 50) == "abaixo" and ff.faixa(33, 50) == "bem_abaixo"


def test_as_regras_decidem_sobre_os_inteiros_mostrados():
    assert ff.inteiro(44.5) == 45 and ff.inteiro(44.49) == 44 and ff.inteiro(0.4) == 0
    f = ff.frase_forma(_serie(40.0, 44.49, 44.5))  # mostrados: 44 e 45 (parecidos), nunca "acima" por um decimal
    assert f.tipo == "parecidos" and "(45)" in f.texto and "(44)" in f.texto


# ---------- a frase inteira, na ordem das regras ----------

def test_r0_serie_vazia_nao_tem_frase():
    assert ff.frase_forma(sc.SerieCarga(sc.VERSAO, [], None)) is None


def test_r1_aprendendo_usa_o_texto_existente_e_nao_compara():
    serie = _serie(30.0, 40.0, 60.0, n=30)  # 30 dias: aprendendo
    f = ff.frase_forma(serie, pendentes=3)
    assert (f.tipo, f.tendencia) == ("aprendendo", None)
    assert f.texto == aprendendo_texto(sc.DIAS_APRENDENDO - 29)  # sem faixa, sem tendencia e sem aviso
    assert "acima" not in f.texto and "pendente" not in f.texto


def test_r2_sem_carga_calculada_nos_14_dias_e_os_avisos_valem():
    dias = [_dia(i, 30.0, 12.0, aprendendo=i < 42, calculadas=0 if i >= 46 else 1) for i in range(60)]
    serie = sc.SerieCarga(sc.VERSAO, dias, None)
    f = ff.frase_forma(serie, pendentes=1)
    assert f.tipo == "sem_treino_recente" and f.tendencia is None
    assert f.texto == ("Você não teve treino com carga calculada nos últimos 14 dias. Seu condicionamento está em 30 e sua fadiga em 12. "
                       "Há 1 treino ainda sem carga calculada; a frase pode mudar quando ele for calculado.")


def test_faixa_mais_tendencia_texto_exato_do_exemplo_da_lia_adaptado():
    f = ff.frase_forma(_serie(39.0, 44.0, 58.0))
    assert (f.tipo, f.tendencia) == ("acima", "subiu")
    assert f.texto == ("Sua fadiga (58) está acima do seu condicionamento (44): seus últimos dias tiveram mais carga do que o seu ritmo das últimas semanas. "
                       "Em 14 dias, seu condicionamento subiu de 39 para 44.")


@pytest.mark.parametrize("f,c,tipo,trecho", [
    (52, 50, "parecidos", "estão parecidos."),
    (80, 50, "bem_acima", "está bem acima do seu condicionamento (50): seus últimos dias tiveram bem mais carga"),
    (30, 50, "bem_abaixo", "está bem abaixo do seu condicionamento (50): seus últimos dias tiveram bem menos carga"),
    (44, 50, "abaixo", "está abaixo do seu condicionamento (50): seus últimos dias tiveram menos carga"),
])
def test_cada_faixa_tem_o_seu_texto(f, c, tipo, trecho):
    r = ff.frase_forma(_serie(50.0, float(c), float(f)))
    assert r.tipo == tipo and trecho in r.texto and r.texto.endswith("ficou perto de 50.")


def test_tendencia_omitida_quando_o_primeiro_dia_do_grafico_ainda_aprendia():
    serie = _serie(40.0, 44.0, 50.0, n=50)  # o grafico comeca no dia 36: ainda aprendendo
    f = ff.frase_forma(serie)
    assert f.tipo == "acima" and f.tendencia is None and "Em 14 dias" not in f.texto


def test_avisos_pendentes_antes_do_sem_carga_com_singular_e_plural():
    um = ff.frase_forma(_serie(40.0, 44.0, 44.0, calculadas=1, sem_carga=1), pendentes=1)
    assert um.texto.endswith("Há 1 treino ainda sem carga calculada; a frase pode mudar quando ele for calculado. "
                             "1 treino dos últimos 14 dias ficou sem carga calculada; os números podem estar subestimados.")
    varios = ff.frase_forma(_serie(40.0, 44.0, 44.0, calculadas=1, sem_carga=3), pendentes=2)
    assert "Há 2 treinos ainda sem carga calculada; a frase pode mudar quando forem calculados. 3 treinos dos últimos 14 dias ficaram sem carga calculada;" in varios.texto
    nenhum = ff.frase_forma(_serie(40.0, 44.0, 44.0))
    assert "sem carga calculada" not in nenhum.texto


def test_modalidade_sem_carga_nao_conta_no_aviso():
    ativs = [sc.AtividadeCarga(D0, 50.0)] + [sc.AtividadeCarga(D0 + timedelta(days=i), motivo="modalidade_sem_carga") for i in (50, 51)]
    serie = sc.calcular_serie(ativs, ate=D0 + timedelta(days=60))
    assert sum(d.sem_carga for d in serie.dias) == 2 and sum(d.sem_carga_avisavel for d in serie.dias) == 0
    comfc = sc.calcular_serie([sc.AtividadeCarga(D0, 50.0), sc.AtividadeCarga(D0 + timedelta(days=55), motivo="sem_fc")], ate=D0 + timedelta(days=60))
    assert sum(d.sem_carga_avisavel for d in comfc.dias) == 1


# ---------- textos: sem sigla, sem conselho, sem adjetivo de valor ----------

def _todos_os_textos():
    out = [ff.TEXTO_SEM_TREINO, ff.AVISO_PENDENTES_UM, ff.AVISO_PENDENTES_VARIOS, ff.AVISO_SEM_CARGA_UM, ff.AVISO_SEM_CARGA_VARIOS]
    out += list(ff.TEXTOS_FAIXA.values()) + list(ff.TEXTOS_TENDENCIA.values())
    return out


PROIBIDAS = re.compile(r"\b(CTL|ATL|TSB|TSS|PMC)\b", re.I)
CONSELHO = re.compile(r"\b(deve|deveria|devia|evite|evitar|descanse|descansar|recomend\w*|sugiro|sugerimos|aconselh\w*|precisa|importante|cuidado|risco|lesão|lesao|"
                      r"melhor|pior|bom|boa|ruim|ótimo|otimo|perigo\w*|treine|reduza|aumente|diminua)\b", re.I)


@pytest.mark.parametrize("texto", _todos_os_textos())
def test_texto_fixo_sem_sigla_e_sem_conselho(texto):
    assert not PROIBIDAS.search(texto), texto
    assert not CONSELHO.search(texto), texto


def test_toda_frase_gerada_tambem_passa_no_teste_de_sigla_e_conselho():
    for f, c in [(52, 50), (60, 50), (80, 50), (30, 50), (44, 50), (5, 5), (3, 40)]:
        for pend, sc_n in [(0, 0), (1, 1), (4, 2)]:
            r = ff.frase_forma(_serie(40.0, float(c), float(f), calculadas=1, sem_carga=sc_n), pendentes=pend)
            assert not PROIBIDAS.search(r.texto) and not CONSELHO.search(r.texto), r.texto


# ---------- serie_carga@2: ate ontem ----------

def test_a_serie_segue_ate_ontem_com_carga_zero_e_decaimento():
    s = sc.calcular_serie([sc.AtividadeCarga(D0, 100.0)], ate=D0 + timedelta(days=10))
    assert len(s.dias) == 11 and s.dias[-1].dia == D0 + timedelta(days=10)
    assert all(d.carga == 0 and d.atividades == 0 for d in s.dias[1:])
    assert s.dias[1].ctl < s.dias[0].ctl and s.dias[1].atl < s.dias[0].atl and s.dias[10].atl < s.dias[1].atl
    assert s.dias[-1].tsb == pytest.approx(s.dias[-1].ctl - s.dias[-1].atl)
    # a conta dos dias do meio e a mesma da serie sem extensao
    base = sc.calcular_serie([sc.AtividadeCarga(D0, 100.0)])
    assert len(base.dias) == 1 and base.dias[0].ctl == s.dias[0].ctl


def test_ate_antes_do_ultimo_dia_com_atividade_nao_encurta_a_serie():
    ativs = [sc.AtividadeCarga(D0, 50.0), sc.AtividadeCarga(D0 + timedelta(days=5), 60.0)]
    assert sc.calcular_serie(ativs, ate=D0 + timedelta(days=2)).dias[-1].dia == D0 + timedelta(days=5)


# ---------- "hoje" no fuso da atividade mais recente, com reserva ----------

def test_hoje_no_fuso_da_atividade_mais_recente_e_reserva_em_sao_paulo():
    agora = datetime(2026, 11, 18, 2, 30, tzinfo=timezone.utc)
    assert hoje_do_atleta(-180, agora) == date(2026, 11, 17)  # 23:30 do dia 17 em UTC-3
    assert hoje_do_atleta(540, agora) == date(2026, 11, 18)  # UTC+9
    assert hoje_do_atleta(None, agora) == date(2026, 11, 17)  # America/Sao_Paulo
    assert hoje_do_atleta(0, datetime(2026, 11, 18, 23, 59, tzinfo=timezone.utc)) == date(2026, 11, 18)
