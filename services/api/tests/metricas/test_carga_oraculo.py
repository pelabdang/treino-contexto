"""Oráculo da carga (rTSS, hrTSS, CTL, ATL e TSB) com as fixtures sintéticas de algumas semanas (issue #137).

Lê as tabelas de voltas de ``tests/fixtures/garmin/gerar_fixtures_carga.py`` e os zips de ``tests/fixtures/garmin/carga/``.
``ESPERADO`` guarda, por atividade, o resultado que a carga deve dar, calculado à mão (a conta de cada volta está em
``docs/metricas/carga-oraculo.md``). As funções de carga (#138) e de série (#139), o comando (#141), a API (#142)
e o QA reaproveitam ``ESPERADO``, ``SEM_SAUDE``, ``CARGA_DIA``, ``SERIE`` e ``TOTAIS``.

Este teste NÃO roda o código da carga (que ainda não existe): confere que o oráculo é coerente com o gerador (voltas,
data local, modalidade), com as regras da ADR 0010 (reimplementadas aqui de forma curta e independente, em
``_referencia``) e com o que o leitor de FIT lê dos arquivos.

Fórmulas e fontes (ADR 0010, itens 4 a 7):
  v_i = distância_i / duração_i ;  IF_i = v_i / velocidade_limiar  (rTSS)  ou  fc_i / fc_limiar  (hrTSS)
  carga_i = duração_i / 3600 x IF_i^2 x 100       (forma do TSS: TSS = horas x IF^2 x 100; Coggan & Allen,
      *Training and Racing with a Power Meter*, e TrainingPeaks, "The Development of the Training Stress Score".
      O hrTSS é adaptação própria, NÃO é o hrTSS por zonas do TrainingPeaks.)
  carga da atividade = soma das voltas; volta sem o dado conta 0; o método só vale com cobertura >= 95% da duração.
  CTL_d = CTL_(d-1) + (L_d - CTL_(d-1)) x (1 - exp(-1/42)) ; ATL igual com 7 ; TSB_d = CTL_d - ATL_d (mesmo dia).
  Forma fechada (sem recursão): CTL_d = k x soma_j L_j x exp(-(d-j)/42), k = 1 - exp(-1/42).
  Base teórica: modelo de impulso-resposta de Banister, Calvert, Savage e Bach, IEEE Trans. SMC-6(2):94-102, 1976.
Limiar (valor vigente é o do último registro com data <= dia local da atividade; antes do primeiro, não há limiar):
  FC (bpm): 05/03 158, 08/03 159, 10/03 163.   Velocidade (m/s): 05/03 3,70, 10/03 3,85 (a de 08/03 não mudou).
"""

import importlib.util
import io
import math
import sys
import zipfile
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.ingestao.garmin.tipos import de_json

RAIZ = Path(__file__).parents[4] / "tests" / "fixtures" / "garmin"
GERADOR = RAIZ / "gerar_fixtures_carga.py"
PASTA = RAIZ / "carga"
COBERTURA_MIN = Fraction(95, 100)
TOL = 1e-6  # os valores abaixo têm 6 casas
TOL_SOMA = 1e-5  # soma de até 20 valores arredondados a 6 casas
TAU_CTL, TAU_ATL = 42, 7

# Limiar vigente (escrito à mão a partir da linha do tempo do gerador de saúde): (a partir de, valor)
LIMIAR_FC = [(date(2025, 3, 5), 158), (date(2025, 3, 8), 159), (date(2025, 3, 10), 163)]
LIMIAR_VELOCIDADE = [(date(2025, 3, 5), Fraction(37, 10)), (date(2025, 3, 10), Fraction(385, 100))]


class Esperado(NamedTuple):
    dia: date  # dia LOCAL (inicio + fuso)
    modalidade: str
    subtipo: str | None
    estado: str  # calculada | sem_carga
    motivo: str | None
    metodo: str | None  # rtss | hrtss
    carga: float | None
    carga_rtss: float | None  # só se o método valeu (limiar e cobertura)
    carga_hrtss: float | None
    cobertura_pct: float | None  # do método vencedor; em sem_carga só para cobertura_insuficiente
    granularidade: str  # volta | atividade
    voltas_rtss: tuple | None  # carga de cada volta (0.0 = volta sem dado)
    voltas_hrtss: tuple | None


# id -> resultado, à mão (docs/metricas/carga-oraculo.md). Fora daqui: ``IGNORADAS_MULTIESPORTE`` do gerador.
ESPERADO = {
    4000000001: Esperado(date(2025, 3, 3), "corrida", None, "sem_carga", "sem_limiar_na_data", None, None, None, None, None, "volta", None, None),
    4000000002: Esperado(date(2025, 3, 4), "corrida", None, "sem_carga", "sem_limiar_na_data", None, None, None, None, None, "volta", None, None),
    4000000003: Esperado(date(2025, 3, 5), "corrida", None, "calculada", None, "rtss", 37.246346, 37.246346, 44.641420, 100.0, "volta", (11.272534, 7.957083, 2.164326, 8.051810, 2.164326, 5.636267), (13.539497, 7.724874, 3.755408, 7.914116, 3.856220, 7.851306)),
    4000000004: Esperado(date(2025, 3, 6), "natacao", None, "sem_carga", "modalidade_sem_carga", None, None, None, None, None, "volta", None, None),
    4000000005: Esperado(date(2025, 3, 7), "ciclismo", None, "calculada", None, "hrtss", 99.768667, None, 99.768667, 100.0, "volta", None, (24.034610, 60.086525, 15.647532)),
    4000000006: Esperado(date(2025, 3, 8), "corrida", None, "calculada", None, "rtss", 41.274471, 41.274471, None, 100.0, "volta", (6.763520, 6.808913, 6.854919, 6.901551, 6.948822, 6.996745), None),
    4000000007: Esperado(date(2025, 3, 8), "corrida", 'esteira', "sem_carga", "sem_fc", None, None, None, None, None, "volta", None, None),
    4000000008: Esperado(date(2025, 3, 10), "corrida", None, "calculada", None, "rtss", 40.111469, 40.111469, 47.566910, 100.0, "volta", (7.808449, 7.808449, 1.874028, 7.874067, 1.874028, 7.940796, 4.931652), (10.289247, 7.251559, 3.763785, 7.361328, 3.864822, 7.470210, 7.565960)),
    4000000009: Esperado(date(2025, 3, 11), "ciclismo", None, "calculada", None, "hrtss", 69.857102, None, 69.857102, 100.0, "volta", None, (19.603046, 41.220972, 9.033084)),
    4000000010: Esperado(date(2025, 3, 12), "corrida", 'esteira', "sem_carga", "cobertura_insuficiente", None, None, None, None, 90.0, "volta", None, None),
    4000000011: Esperado(date(2025, 3, 13), "corrida", 'esteira', "calculada", None, "hrtss", 22.949469, None, 22.949469, 95.0, "volta", None, (1.176183, 1.191917, 1.207757, 1.223701, 1.239749, 1.176183, 1.191917, 0.0, 1.223701, 1.239749, 1.176183, 1.191917, 1.207757, 1.223701, 1.239749, 1.176183, 1.191917, 1.207757, 1.223701, 1.239749)),
    4000000012: Esperado(date(2025, 3, 14), "corrida", None, "sem_carga", "sem_pace", None, None, None, None, None, "volta", None, None),
    4000000014: Esperado(date(2025, 3, 15), "natacao", None, "sem_carga", "modalidade_sem_carga", None, None, None, None, None, "atividade", None, None),
    4000000016: Esperado(date(2025, 3, 15), "ciclismo", None, "calculada", None, "hrtss", 49.987768, None, 49.987768, 100.0, "volta", None, (14.702285, 35.285483)),
    4000000018: Esperado(date(2025, 3, 15), "corrida", None, "calculada", None, "rtss", 22.670675, 22.670675, 22.479063, 100.0, "volta", (7.496111, 7.556564, 7.617999), (7.377018, 7.493277, 7.608767)),
    4000000019: Esperado(date(2025, 3, 16), "corrida", None, "calculada", None, "hrtss", 54.668975, None, 54.668975, 100.0, "volta", None, (12.295031, 13.188929, 14.114193, 15.070822)),
    4000000023: Esperado(date(2025, 3, 20), "corrida", None, "calculada", None, "rtss", 31.233797, 31.233797, 35.285483, 100.0, "atividade", (31.233797,), (35.285483,)),
    4000000020: Esperado(date(2025, 4, 5), "corrida", None, "calculada", None, "rtss", 20.998335, 20.998335, 29.891486, 100.0, "volta", (5.205633, 5.234715, 5.264123, 5.293864), (7.377018, 7.441210, 7.504970, 7.568288)),
    4000000021: Esperado(date(2025, 4, 15), "corrida", None, "calculada", None, "rtss", 16.155768, 16.155768, 22.319566, 100.0, "volta", (5.354365, 5.385137, 5.416265), (7.378482, 7.440012, 7.501073)),
    4000000022: Esperado(date(2025, 4, 16), "corrida", None, "calculada", None, "rtss", 21.919391, 21.919391, 30.277247, 100.0, "volta", (5.431965, 5.463638, 5.495683, 5.528106), (7.479393, 7.539671, 7.599454, 7.658728)),
}

# Atleta sem nenhum dado de saúde (exportacao_carga_sem_saude.zip): nenhuma atividade calculada. Natação continua
# modalidade_sem_carga porque essa regra vem antes do limiar (ADR 0010, item 7, passo 2).
SEM_SAUDE = {
    id_: ("modalidade_sem_carga" if e.modalidade == "natacao" else "sem_dados_saude") for id_, e in ESPERADO.items()
}

# Carga diária: soma das cargas calculadas por dia local (dias que não aparecem têm 0).
CARGA_DIA = {
    date(2025, 3, 5): 37.246346,
    date(2025, 3, 7): 99.768667,
    date(2025, 3, 8): 41.274471,
    date(2025, 3, 10): 40.111469,
    date(2025, 3, 11): 69.857102,
    date(2025, 3, 13): 22.949469,
    date(2025, 3, 15): 72.658442,
    date(2025, 3, 16): 54.668975,
    date(2025, 3, 20): 31.233797,
    date(2025, 4, 5): 20.998335,
    date(2025, 4, 15): 16.155768,
    date(2025, 4, 16): 21.919391,
}


class Dia(NamedTuple):
    carga: float
    ctl: float
    atl: float
    tsb: float
    aprendendo: bool  # dias desde o primeiro dia da série < 42
    atividades: int  # elegíveis (sem multiesporte_pai e troca) com dia local = este
    calculadas: int
    sem_carga: int


# Série de 05/03 (primeiro dia com carga calculada) a 16/04 (dia da última atividade): 43 dias. Dias escolhidos.
SERIE = {
    date(2025, 3, 5): Dia(37.246346, 0.876344, 4.958312, -4.081968, True, 1, 1, 0),
    date(2025, 3, 8): Dia(41.274471, 4.079208, 20.237947, -16.158739, True, 2, 1, 1),
    date(2025, 3, 9): Dia(0.000000, 3.983231, 17.543829, -13.560598, True, 0, 0, 0),
    date(2025, 3, 15): Dia(72.658442, 8.009499, 27.279020, -19.269521, True, 3, 2, 1),
    date(2025, 4, 5): Dia(20.998335, 6.653098, 4.994324, 1.658774, True, 1, 1, 0),
    date(2025, 4, 15): Dia(16.155768, 5.623609, 3.347585, 2.276024, True, 1, 1, 0),
    date(2025, 4, 16): Dia(21.919391, 6.007021, 5.819903, 0.187118, False, 1, 1, 0),
}
PRIMEIRO_DIA, ULTIMO_DIA = date(2025, 3, 5), date(2025, 4, 16)

TOTAIS = {
    "atividades_importadas": 23,
    "ignoradas_multiesporte": 3,
    "calculadas": 13,
    "sem_carga_total": 7,
    "por_motivo": {
        "sem_dados_saude": 0,
        "sem_limiar_na_data": 2,
        "sem_fc": 1,
        "sem_pace": 1,
        "cobertura_insuficiente": 1,
        "modalidade_sem_carga": 2,
    },
}
TOTAIS_SEM_SAUDE = {
    "calculadas": 0,
    "sem_carga_total": 20,
    "por_motivo": {
        "sem_dados_saude": 18,
        "sem_limiar_na_data": 0,
        "sem_fc": 0,
        "sem_pace": 0,
        "cobertura_insuficiente": 0,
        "modalidade_sem_carga": 2,
    },
}
MOTIVOS = {"sem_dados_saude", "sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga"}


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures_carga", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _vigente(tabela, dia):
    valor = None
    for desde, v in tabela:
        if desde <= dia:
            valor = v
    return valor


def _dia_local(a):
    return (a.inicio + timedelta(hours=a.fuso_h)).date()


def _voltas(a):
    """Voltas da atividade; sem FIT, uma volta única com os totais do JSON (ADR 0010, item 4)."""
    if a.voltas:
        return [(Fraction(v[1]).limit_denominator(10**6), Fraction(v[2]), v[3]) for v in a.voltas]
    dist, dur, fc = a.json_total
    return [(Fraction(dist), Fraction(dur), fc)]


def _cargas_voltas(metodo, voltas, limiar):
    """Carga de cada volta (0 para volta sem o dado) e cobertura (fração da duração com dado)."""
    cargas, coberto = [], Fraction(0)
    for dist, dur, fc in voltas:
        if metodo == "rtss":
            tem = dist > 0 and dur > 0
            intensidade = (dist / dur) / limiar if tem else None
        else:
            tem = fc is not None and dur > 0
            intensidade = Fraction(fc) / limiar if tem else None
        if tem:
            coberto += dur
            cargas.append(dur / 3600 * intensidade**2 * 100)
        else:
            cargas.append(Fraction(0))
    return cargas, coberto / sum(d for _, d, _ in voltas)


def _referencia(a, modalidade, subtipo):
    """Resultado esperado pela ADR 0010 (itens 4 e 7), calculado só com as tabelas do gerador. Retorna um dict."""
    dia = _dia_local(a)
    if modalidade in ("natacao", "outra"):
        return {"estado": "sem_carga", "motivo": "modalidade_sem_carga"}
    caminhos = [("rtss", _vigente(LIMIAR_VELOCIDADE, dia))] if modalidade == "corrida" and subtipo != "esteira" else []
    caminhos.append(("hrtss", _vigente(LIMIAR_FC, dia)))
    disponiveis = [(m, lim) for m, lim in caminhos if lim is not None]
    if not disponiveis:
        return {"estado": "sem_carga", "motivo": "sem_limiar_na_data"}
    voltas = _voltas(a)
    por_metodo = {}
    for metodo, lim in disponiveis:
        cargas, cob = _cargas_voltas(metodo, voltas, lim)
        por_metodo[metodo] = (cargas, cob, cob >= COBERTURA_MIN)
    validos = [m for m, (_, _, ok) in por_metodo.items() if ok]
    if not validos:
        primeiro = disponiveis[0][0]
        cob = por_metodo[primeiro][1]
        if cob == 0:
            return {"estado": "sem_carga", "motivo": "sem_pace" if primeiro == "rtss" else "sem_fc"}
        return {"estado": "sem_carga", "motivo": "cobertura_insuficiente", "cobertura": cob}
    venc = validos[0]
    return {
        "estado": "calculada", "metodo": venc, "cobertura": por_metodo[venc][1],
        "por_metodo": {m: p for m, p in por_metodo.items() if p[2]},
    }


# ---------------------------------------------------------------------------------------------------
# Coerência do oráculo com o gerador
# ---------------------------------------------------------------------------------------------------
def _elegiveis(gerador):
    return [a for a in gerador.ATIVIDADES if a.id not in gerador.IGNORADAS_MULTIESPORTE]


def test_oraculo_cobre_todas_as_atividades_do_gerador(gerador):
    ids = {a.id for a in gerador.ATIVIDADES}
    assert len(ids) == len(gerador.ATIVIDADES) == TOTAIS["atividades_importadas"]
    assert set(ESPERADO) == ids - set(gerador.IGNORADAS_MULTIESPORTE)
    assert len(gerador.IGNORADAS_MULTIESPORTE) == TOTAIS["ignoradas_multiesporte"]


def test_dia_local_modalidade_e_subtipo(gerador):
    """A modalidade e o subtipo saem do tipo do JSON, e o dia é o local (inicio UTC + fuso)."""
    for a in gerador.ATIVIDADES:
        modalidade, subtipo = de_json(a.activity_type, a.sport_type)
        if a.id in gerador.IGNORADAS_MULTIESPORTE:
            assert (modalidade, subtipo) in {("outra", "multiesporte_pai"), ("outra", "troca")}
            continue
        e = ESPERADO[a.id]
        assert e.dia == _dia_local(a), a.id
        assert e.modalidade == modalidade, a.id
        assert e.subtipo == (subtipo if subtipo == "esteira" else None), a.id


def test_dia_local_difere_do_dia_utc_em_dois_casos(gerador):
    """04/03 22h local (05/03 01h UTC) e 11/03 23h local (12/03 02h UTC): o dia vale o local."""
    ids = {a.id for a in gerador.ATIVIDADES if a.inicio.date() != _dia_local(a)}
    assert ids == {4000000002, 4000000009}
    assert ESPERADO[4000000002].dia == date(2025, 3, 4) and ESPERADO[4000000009].dia == date(2025, 3, 11)


def test_limiar_do_oraculo_bate_com_a_fixture_de_saude(gerador):
    """As tabelas de limiar do teste são as do gerador de saúde (velocidade do arquivo = m/s / 10)."""
    saude = gerador.saude
    for dia in (date(2025, 3, 4) + timedelta(days=i) for i in range(45)):
        assert _vigente(LIMIAR_FC, dia) == saude.fc_limiar_em(dia), dia
    registros = [(d, v) for d, _, v in saude.LIMIARES if v is not None]
    assert [(d, Fraction(round(v * 1000), 100)) for d, v in registros] == LIMIAR_VELOCIDADE


@pytest.mark.parametrize("id_", sorted(ESPERADO))
def test_esperado_bate_com_a_referencia_da_adr(gerador, id_):
    a = next(x for x in gerador.ATIVIDADES if x.id == id_)
    e = ESPERADO[id_]
    ref = _referencia(a, e.modalidade, e.subtipo)
    assert e.estado == ref["estado"]
    if e.estado == "sem_carga":
        assert e.motivo == ref["motivo"]
        assert e.metodo is None and e.carga is None and e.carga_rtss is None and e.carga_hrtss is None
        if e.motivo == "cobertura_insuficiente":
            assert e.cobertura_pct == pytest.approx(float(ref["cobertura"]) * 100, abs=1e-9)
        else:
            assert e.cobertura_pct is None
        return
    assert e.motivo is None and e.metodo == ref["metodo"]
    assert e.cobertura_pct == pytest.approx(float(ref["cobertura"]) * 100, abs=1e-9)
    assert e.granularidade == ("volta" if a.voltas else "atividade")
    for metodo, (cargas, _, _) in ref["por_metodo"].items():
        total = e.carga_rtss if metodo == "rtss" else e.carga_hrtss
        por_volta = e.voltas_rtss if metodo == "rtss" else e.voltas_hrtss
        assert total == pytest.approx(float(sum(cargas)), abs=TOL)
        assert list(por_volta) == pytest.approx([float(c) for c in cargas], abs=TOL)
        assert total == pytest.approx(sum(por_volta), abs=TOL_SOMA)
    for metodo, total in (("rtss", e.carga_rtss), ("hrtss", e.carga_hrtss)):
        if metodo not in ref["por_metodo"]:
            assert total is None  # o método não valeu: nada gravado
    assert e.carga == pytest.approx(e.carga_rtss if e.metodo == "rtss" else e.carga_hrtss, abs=TOL)


def test_oraculo_cobre_os_seis_motivos_e_os_dois_metodos():
    motivos = {e.motivo for e in ESPERADO.values() if e.motivo} | set(SEM_SAUDE.values())
    assert motivos == MOTIVOS
    assert {e.metodo for e in ESPERADO.values() if e.metodo} == {"rtss", "hrtss"}
    assert {e.granularidade for e in ESPERADO.values()} >= {"volta", "atividade"}


def test_regras_de_escolha_do_metodo():
    """rTSS vence quando os dois valem; esteira e ciclismo só hrTSS; ambos gravados quando os dois valem."""
    for e in ESPERADO.values():
        if e.estado != "calculada":
            continue
        if e.carga_rtss is not None:
            assert e.metodo == "rtss" and e.modalidade == "corrida" and e.subtipo != "esteira"
        if e.subtipo == "esteira" or e.modalidade == "ciclismo":
            assert e.carga_rtss is None and e.metodo == "hrtss"
    # 05/03: os dois valem (rTSS vence); 16/03: sem distância, só hrTSS
    assert ESPERADO[4000000003].carga == ESPERADO[4000000003].carga_rtss != ESPERADO[4000000003].carga_hrtss
    assert ESPERADO[4000000019].carga_rtss is None and ESPERADO[4000000019].metodo == "hrtss"
    # a cobertura de 95% vale (a volta sem FC conta 0) e a de 90% não
    assert ESPERADO[4000000011].estado == "calculada" and ESPERADO[4000000011].cobertura_pct == 95.0
    assert ESPERADO[4000000010].motivo == "cobertura_insuficiente" and ESPERADO[4000000010].cobertura_pct == 90.0


def test_exemplos_da_adr_0010():
    """Exemplos 1 a 3 da ADR, calculados aqui à mão: as mesmas fórmulas dão os números do texto."""
    vl = Fraction(1000, 270)
    a = Fraction(300, 3600) * (Fraction(1000, 300) / vl) ** 2 * 100
    b = Fraction(240, 3600) * (Fraction(1000, 240) / vl) ** 2 * 100
    assert float(a) == pytest.approx(6.75) and float(b) == pytest.approx(8.4375) and float(a + b) == pytest.approx(15.1875)
    assert float(Fraction(3600, 3600) * (Fraction(1000, 270) / vl) ** 2 * 100) == pytest.approx(100)  # 1 h no limiar
    ha = Fraction(300, 3600) * (Fraction(153, 170)) ** 2 * 100
    hb = Fraction(240, 3600) * (Fraction(187, 170)) ** 2 * 100
    assert float(ha) == pytest.approx(6.75) and float(hb) == pytest.approx(8.0667, abs=1e-4)
    voltas = [(Fraction(100), Fraction(100), 150)] * 9 + [(Fraction(100), Fraction(100), None)]
    assert _cargas_voltas("hrtss", voltas, 170)[1] == Fraction(9, 10) < COBERTURA_MIN
    voltas = [(Fraction(50), Fraction(50), 150)] * 19 + [(Fraction(50), Fraction(50), None)]
    assert _cargas_voltas("hrtss", voltas, 170)[1] == Fraction(95, 100) >= COBERTURA_MIN


# ---------------------------------------------------------------------------------------------------
# Série CTL / ATL / TSB
# ---------------------------------------------------------------------------------------------------
def _serie_por_recursao():
    k_ctl, k_atl = 1 - math.exp(-1 / TAU_CTL), 1 - math.exp(-1 / TAU_ATL)
    ctl = atl = 0.0
    saida, dia = {}, PRIMEIRO_DIA
    while dia <= ULTIMO_DIA:
        carga = CARGA_DIA.get(dia, 0.0)
        ctl += (carga - ctl) * k_ctl
        atl += (carga - atl) * k_atl
        saida[dia] = (carga, ctl, atl, ctl - atl)
        dia += timedelta(days=1)
    return saida


def _serie_forma_fechada(dia):
    k_ctl, k_atl = 1 - math.exp(-1 / TAU_CTL), 1 - math.exp(-1 / TAU_ATL)
    ctl = k_ctl * sum(c * math.exp(-(dia - d).days / TAU_CTL) for d, c in CARGA_DIA.items() if d <= dia)
    atl = k_atl * sum(c * math.exp(-(dia - d).days / TAU_ATL) for d, c in CARGA_DIA.items() if d <= dia)
    return ctl, atl


def test_carga_diaria_soma_as_calculadas_do_dia_local():
    soma = {}
    for e in ESPERADO.values():
        if e.estado == "calculada":
            soma[e.dia] = soma.get(e.dia, 0.0) + e.carga
    assert set(soma) == set(CARGA_DIA)
    for dia, valor in soma.items():
        assert CARGA_DIA[dia] == pytest.approx(valor, abs=TOL_SOMA)
    assert min(CARGA_DIA) == PRIMEIRO_DIA  # a série começa no primeiro dia com carga calculada
    # a série termina no dia da última atividade importada (calculada ou não)
    assert ULTIMO_DIA == max(e.dia for e in ESPERADO.values())


def test_serie_dos_dias_escolhidos():
    por_recursao = _serie_por_recursao()
    assert len(por_recursao) == 43
    for dia, esperado in SERIE.items():
        carga, ctl, atl, tsb = por_recursao[dia]
        assert esperado.carga == pytest.approx(carga, abs=TOL)
        assert esperado.ctl == pytest.approx(ctl, abs=TOL)
        assert esperado.atl == pytest.approx(atl, abs=TOL)
        assert esperado.tsb == pytest.approx(tsb, abs=TOL)
        assert esperado.tsb == pytest.approx(esperado.ctl - esperado.atl, abs=TOL)  # TSB do mesmo dia
        # a conta à mão (forma fechada) dá o mesmo que a recursão
        f_ctl, f_atl = _serie_forma_fechada(dia)
        assert esperado.ctl == pytest.approx(f_ctl, abs=TOL) and esperado.atl == pytest.approx(f_atl, abs=TOL)


def test_aprendendo_e_contagens_por_dia():
    for dia, esperado in SERIE.items():
        assert esperado.aprendendo == ((dia - PRIMEIRO_DIA).days < 42), dia
        elegiveis = [e for e in ESPERADO.values() if e.dia == dia]
        assert esperado.atividades == len(elegiveis)
        assert esperado.calculadas == sum(e.estado == "calculada" for e in elegiveis)
        assert esperado.sem_carga == sum(e.estado == "sem_carga" for e in elegiveis)
    assert SERIE[date(2025, 4, 15)].aprendendo is True and SERIE[date(2025, 4, 16)].aprendendo is False
    # dia sem treino: carga 0 e CTL e ATL só decaem
    assert SERIE[date(2025, 3, 9)].atividades == 0 and SERIE[date(2025, 3, 9)].ctl < SERIE[date(2025, 3, 8)].ctl


def test_exemplo_4_da_adr_0010():
    """Cargas 100, 0 e 50 a partir do primeiro dia (conta à mão no texto da ADR)."""
    k_ctl, k_atl = 1 - math.exp(-1 / 42), 1 - math.exp(-1 / 7)
    assert (k_ctl, k_atl) == (pytest.approx(0.023528, abs=1e-6), pytest.approx(0.133122, abs=1e-6))
    ctl = atl = 0.0
    esperado = [(2.3528, 13.3122), (2.2975, 11.5401), (3.4198, 16.6599)]
    for carga, (c, a) in zip((100, 0, 50), esperado):
        ctl += (carga - ctl) * k_ctl
        atl += (carga - atl) * k_atl
        assert (ctl, atl) == (pytest.approx(c, abs=1e-4), pytest.approx(a, abs=1e-4))
    assert ctl - atl == pytest.approx(-13.2401, abs=1e-4)


def test_totais():
    estados = [e for e in ESPERADO.values()]
    assert sum(e.estado == "calculada" for e in estados) == TOTAIS["calculadas"]
    sem = [e for e in estados if e.estado == "sem_carga"]
    assert len(sem) == TOTAIS["sem_carga_total"]
    assert TOTAIS["calculadas"] + TOTAIS["sem_carga_total"] + TOTAIS["ignoradas_multiesporte"] == TOTAIS["atividades_importadas"]
    for motivo, n in TOTAIS["por_motivo"].items():
        assert sum(e.motivo == motivo for e in sem) == n
    # atleta sem saúde: nenhuma calculada, série vazia
    assert len(SEM_SAUDE) == TOTAIS_SEM_SAUDE["sem_carga_total"]
    for motivo, n in TOTAIS_SEM_SAUDE["por_motivo"].items():
        assert list(SEM_SAUDE.values()).count(motivo) == n


# ---------------------------------------------------------------------------------------------------
# Os zips versionados batem com o gerador e com o leitor de FIT
# ---------------------------------------------------------------------------------------------------
def test_zips_versionados_sao_os_do_gerador(gerador):
    assert (PASTA / "exportacao_carga.zip").read_bytes() == gerador.montar_exportacao_carga()
    assert (PASTA / "exportacao_carga_sem_saude.zip").read_bytes() == gerador.montar_exportacao_carga_sem_saude()


def _membros(caminho):
    with zipfile.ZipFile(caminho) as z:
        return {n: z.read(n) for n in z.namelist()}


def test_zip_sem_saude_nao_tem_arquivos_de_saude(gerador):
    com, sem = _membros(PASTA / "exportacao_carga.zip"), _membros(PASTA / "exportacao_carga_sem_saude.zip")
    assert any("DI-Connect-Wellness" in n for n in com)
    assert not any("Wellness" in n or "DI-Connect-Metrics" in n or "personalRecord" in n for n in sem)
    assert sem[gerador.base.CAMINHO_JSON] == com[gerador.base.CAMINHO_JSON]  # mesmas atividades


def test_leitor_de_fit_le_as_voltas_da_tabela(gerador):
    membros = _membros(PASTA / "exportacao_carga.zip")
    with zipfile.ZipFile(io.BytesIO(membros[gerador.base.CAMINHO_UPLOADS])) as z:
        fits = {n: z.read(n) for n in z.namelist()}
    com_fit = [a for a in gerador.ATIVIDADES if a.voltas is not None]
    assert len(fits) == len(com_fit)
    for a in com_fit:
        lido = ler_fit(fits[f"atleta-ficticio_{a.id}.fit"])
        assert [(v.distancia_m, v.duracao_s, v.fc_media) for v in lido.voltas] == [
            (float(v[1]), float(v[2]), v[3]) for v in a.voltas
        ], a.id
