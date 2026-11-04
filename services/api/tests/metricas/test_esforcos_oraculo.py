"""Oráculo da detecção de esforços com as fixtures sintéticas (issue #161; ADR 0008).

Lê as tabelas ``VOLTAS_E1..E7`` de ``tests/fixtures/garmin/gerar_fixtures.py`` e os FIT de
``tests/fixtures/garmin/esforcos/``. ``ESPERADO`` guarda, por atividade, os blocos que a detecção deve devolver,
calculados à mão (a conta está em ``docs/metricas/esforcos-oraculo.md``). As funções de blocos (#162), de corrida
(#163), de ciclismo (#164 e #165), o comando e a API (#166 e seguintes) e o QA reaproveitam ``ESPERADO``.

Este teste NÃO roda a detecção: confere que o oráculo é coerente com o gerador (somando as voltas de cada bloco),
com as regras da ADR 0008 (limiar, faixas, posição da categoria) e com o que o leitor de FIT lê do arquivo.

Fórmulas (ADR 0008, item 1; regras próprias do projeto, sem artigo):
  pace do bloco (s/km)  = soma(duração) / soma(distância) x 1000     (nunca a média dos paces das voltas)
  velocidade (km/h)     = soma(distância) / soma(duração) x 3,6
  FC do bloco (bpm)     = soma(FC x duração) / soma(duração)
  parada_apos_s do bloco = parada depois da última volta do bloco
"""

import importlib.util
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.ingestao.garmin.tipos import de_fit

RAIZ = Path(__file__).parents[4] / "tests" / "fixtures" / "garmin"
GERADOR = RAIZ / "gerar_fixtures.py"
PASTA_FIT = RAIZ / "esforcos"


class Bloco(NamedTuple):
    categoria: str
    volta_inicial: int  # segmento.ordem da primeira volta (a partir de 0, como o leitor de FIT)
    volta_final: int
    distancia_m: float
    duracao_s: float  # tempo em movimento
    intensidade: float  # corrida: pace em s/km; ciclismo: velocidade em km/h
    fc_media: float
    faixa: str | None
    parada_apos_s: float
    treino_chave: bool = False


AQ, ES, RE, DE, LE = "aquecimento", "esforco", "recuperacao", "desaquecimento", "leve"

# --- 1. Corrida, tiros de 400 m com 90 s parados (ADR, exemplo 2) --------------------------------------------
# ref 330 s/km, limiar 330 x 0,90 = 297. Aquecimento 2000 m em 660 s = 330 s/km; cada 400 m em 88 s = 220 s/km
# (220 <= 297: esforço, faixa d400: 370 a 430 m); desaquecimento 1000 m em 340 s = 340 s/km. Nada se junta:
# 90 s parados >= 15 s. Recuperação total = 9 x 90 = 810 s.
_FC_400 = [160, 164, 167, 169, 171, 172, 173, 174, 175, 176]
E1 = (
    [Bloco(AQ, 0, 0, 2000, 660, 330, 130, None, 0)]
    + [Bloco(ES, i, i, 400, 88, 220, fc, "d400", 90 if i < 10 else 0) for i, fc in enumerate(_FC_400, start=1)]
    + [Bloco(DE, 11, 11, 1000, 340, 340, 140, None, 0)]
)

# --- 2. Corrida, 3 x 1500 m cortados pelo lap automático (ADR, exemplo 1) -----------------------------------
# ref 330. Aquecimento: 1000 m a 330 s + 1000 m a 332 s; 332 vs bloco 330 = +0,6% < 5% e sem parada: junta.
#   2000 m, 662 s, pace 662 / 2000 x 1000 = 331,0; FC (128 x 330 + 131 x 332) / 662 = 85732 / 662 = 129,5045.
# Rep 1: 1000 m a 240 s + 500 m a 121 s (242 s/km, +0,8%): 1500 m, 361 s, pace 361 / 1500 x 1000 = 240,6667;
#   FC (165 x 240 + 168 x 121) / 361 = 59928 / 361 = 166,0055. Parada de 120 s separa a rep 2.
# Rep 2: 242 s + 121 s = 363 s, pace 242,0; FC (167 x 242 + 170 x 121) / 363 = 60984 / 363 = 168,0.
# Rep 3: 243 s + 122 s (244 s/km, +0,4%) = 365 s, pace 365 / 1500 x 1000 = 243,3333;
#   FC (168 x 243 + 171 x 122) / 365 = 61686 / 365 = 169,0027.
# Esforço: 240,67, 242, 243,33 <= 297, faixa d1500 (1425 a 1575 m). Desaquecimento 1000 m em 340 s.
E2 = [
    Bloco(AQ, 0, 1, 2000, 662, 331.0, 85732 / 662, None, 0),
    Bloco(ES, 2, 3, 1500, 361, 361 / 1500 * 1000, 59928 / 361, "d1500", 120),
    Bloco(ES, 4, 5, 1500, 363, 242.0, 168.0, "d1500", 120),
    Bloco(ES, 6, 7, 1500, 365, 365 / 1500 * 1000, 61686 / 365, "d1500", 0),
    Bloco(DE, 8, 8, 1000, 340, 340, 138, None, 0),
]

# --- 3. Corrida, treino contínuo forte (ADR, exemplo 3) ----------------------------------------------------
# 8 voltas de 1000 m: 268+271+270+272+269+270+271+269 = 2160 s (todas dentro de 5% do bloco: juntam). Um bloco:
# 8000 m, 2160 s, pace 2160 / 8000 x 1000 = 270,0 <= 297 (ref 330), margem 1 - 270/330 = 18,2%.
# FC x duração: 150x268 + 160x271 + 164x270 + 166x272 + 168x269 + 169x270 + 170x271 + 171x269
#   = 40200 + 43360 + 44280 + 45152 + 45192 + 45630 + 46070 + 45999 = 355883; FC = 355883 / 2160 = 164,7606.
# 2160 s >= 1200 s (CONTINUO_MIN_S): treino-chave. 8000 m passa de d5000 (4750 a 5250): sem faixa.
E3 = [Bloco(ES, 0, 7, 8000, 2160, 270.0, 355883 / 2160, None, 0, treino_chave=True)]

# --- 4. Corrida, rodagem leve de 6 km ------------------------------------------------------------------------
# 355+352+350+351+349+348 = 2105 s; 6000 m; pace 2105 / 6000 x 1000 = 350,8333 > 297: nenhum esforço, tudo leve,
# e os 6 laps juntam (todos a menos de 2% do bloco). FC x duração: 140x355 + 142x352 + 143x350 + 144x351 +
# 145x349 + 146x348 = 49700 + 49984 + 50050 + 50544 + 50605 + 50808 = 301691; FC = 301691 / 2105 = 143,3211.
E4 = [Bloco(LE, 0, 5, 6000, 2105, 2105 / 6000 * 1000, 301691 / 2105, None, 0)]

# --- 5. Corrida, treino misto: 1 km e curtos (ADR item 8, caso 4) ---------------------------------------------
# ref 330, limiar 297. Aquecimento 2000 m em 660 s = 330. 5 x 1000 m em 250 s (250 s/km, d1000) cada um seguido
# de 400 m em 168 s (420 s/km > 297: recuperação). 8 x 400 m em 92 s (230 s/km, d400) com 200 m em 90 s
# (450 s/km, recuperação) entre eles; desaquecimento 1000 m em 340 s. Nenhum par vizinho está a menos de 5%
# (250 vs 420, 420 vs 230, 230 vs 450): 1 volta = 1 bloco, 27 blocos. Sem parada. Pace da sessão dos
# esforços de 1 km = 5 x 250 / 5000 x 1000 = 250 s/km (os d400 não contam para a visão de tiros).
_FC_1K = [160, 163, 165, 167, 168]
_FC_M400 = [170, 172, 173, 174, 175, 176, 177, 178]
E5 = [Bloco(AQ, 0, 0, 2000, 660, 330, 130, None, 0)]
for _fc in _FC_1K:
    _v = len(E5)
    E5 += [Bloco(ES, _v, _v, 1000, 250, 250, _fc, "d1000", 0), Bloco(RE, _v + 1, _v + 1, 400, 168, 420, 145, None, 0)]
for _i, _fc in enumerate(_FC_M400):
    _v = len(E5)
    E5.append(Bloco(ES, _v, _v, 400, 92, 230, _fc, "d400", 0))
    if _i < 7:
        E5.append(Bloco(RE, _v + 1, _v + 1, 200, 90, 450, 150, None, 0))
E5.append(Bloco(DE, len(E5), len(E5), 1000, 340, 340, 140, None, 0))

# --- 6. Ciclismo por duração (ADR, exemplo 4) --------------------------------------------------------------
# ref 22 km/h, limiar 22 x 1,15 = 25,3 km/h. Aquecimento 6250 m em 900 s = 6250 / 900 x 3,6 = 25,0 (< 25,3: não é
# esforço). 5 x (2400 m em 240 s = 36,0 km/h, faixa t4: 221 a 259 s; recuperação 733,33 m em 120 s =
# 733,33 / 120 x 3,6 = 21,9999 km/h). A 5ª recuperação vem depois do último esforço: desaquecimento, e não junta
# com o último bloco, 4000 m em 600 s = 24,0 km/h, porque 24 vs 22 = +9,1% > 5%. Dois blocos de desaquecimento.
_FC_PEDAL = [150, 155, 158, 160, 162]
E6 = [Bloco(AQ, 0, 0, 6250, 900, 25.0, 125, None, 0)]
for _k, _fc in enumerate(_FC_PEDAL):
    _v = 1 + 2 * _k
    E6.append(Bloco(ES, _v, _v, 2400, 240, 36.0, _fc, "t4", 0))
    E6.append(Bloco(DE if _k == 4 else RE, _v + 1, _v + 1, 733.33, 120, 733.33 / 120 * 3.6, 140, None, 0))
E6.append(Bloco(DE, 11, 11, 4000, 600, 24.0, 135, None, 0))

# --- 7. Ciclismo, lap automático cortando um bloco (ADR, exemplo 5) -------------------------------------------
# ref 20 km/h, limiar 20 x 1,15 = 23,0. Aquecimento 3000 m em 600 s = 18,0 km/h. Bloco: 5000 m em 750 s + 3000 m em
# 450 s, os dois a 24,0 km/h (5000 / 750 x 3,6 = 24), sem parada: 8000 m, 1200 s, 8000 / 1200 x 3,6 = 24,0 >= 23,
# faixa t20 (1104 a 1296 s). FC (150 x 750 + 156 x 450) / 1200 = 182700 / 1200 = 152,25.
# Desaquecimento 3000 m em 600 s = 18,0 km/h.
E7 = [
    Bloco(AQ, 0, 0, 3000, 600, 18.0, 120, None, 0),
    Bloco(ES, 1, 2, 8000, 1200, 24.0, 152.25, "t20", 0),
    Bloco(DE, 3, 3, 3000, 600, 18.0, 125, None, 0),
]

# nome do FIT -> (modalidade, referência de intensidade, blocos). Referência: s/km (corrida) ou km/h (ciclismo).
ESPERADO = {
    "esforcos_corrida_400_com_pausa.fit": ("corrida", 330, E1),
    "esforcos_corrida_1500_lap_automatico.fit": ("corrida", 330, E2),
    "esforcos_corrida_continuo_forte.fit": ("corrida", 330, E3),
    "esforcos_corrida_rodagem_leve.fit": ("corrida", 330, E4),
    "esforcos_corrida_misto.fit": ("corrida", 330, E5),
    "esforcos_ciclismo_blocos_4min.fit": ("ciclismo", 22, E6),
    "esforcos_ciclismo_lap_automatico.fit": ("ciclismo", 20, E7),
}
TABELAS = {  # nome do FIT -> nome da tabela de voltas no gerador
    "esforcos_corrida_400_com_pausa.fit": "VOLTAS_E1",
    "esforcos_corrida_1500_lap_automatico.fit": "VOLTAS_E2",
    "esforcos_corrida_continuo_forte.fit": "VOLTAS_E3",
    "esforcos_corrida_rodagem_leve.fit": "VOLTAS_E4",
    "esforcos_corrida_misto.fit": "VOLTAS_E5",
    "esforcos_ciclismo_blocos_4min.fit": "VOLTAS_E6",
    "esforcos_ciclismo_lap_automatico.fit": "VOLTAS_E7",
}
# Faixas da ADR 0008, item 5 (corrida em metros, ciclismo em segundos), só as usadas aqui.
FAIXAS = {"d400": (370, 430), "d1000": (950, 1050), "d1500": (1425, 1575), "t4": (221, 259), "t20": (1104, 1296)}
NUMERO_DE_BLOCOS = {
    "esforcos_corrida_400_com_pausa.fit": 12,
    "esforcos_corrida_1500_lap_automatico.fit": 5,
    "esforcos_corrida_continuo_forte.fit": 1,
    "esforcos_corrida_rodagem_leve.fit": 1,
    "esforcos_corrida_misto.fit": 27,
    "esforcos_ciclismo_blocos_4min.fit": 12,
    "esforcos_ciclismo_lap_automatico.fit": 3,
}
# Contagem por categoria, à mão (aquecimento, esforço, recuperação, desaquecimento, leve).
CATEGORIAS = {
    "esforcos_corrida_400_com_pausa.fit": (1, 10, 0, 1, 0),
    "esforcos_corrida_1500_lap_automatico.fit": (1, 3, 0, 1, 0),
    "esforcos_corrida_continuo_forte.fit": (0, 1, 0, 0, 0),
    "esforcos_corrida_rodagem_leve.fit": (0, 0, 0, 0, 1),
    "esforcos_corrida_misto.fit": (1, 13, 12, 1, 0),
    "esforcos_ciclismo_blocos_4min.fit": (1, 5, 4, 2, 0),
    "esforcos_ciclismo_lap_automatico.fit": (1, 1, 0, 1, 0),
}
NOMES = list(ESPERADO)


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _voltas(gerador, nome):
    return getattr(gerador, TABELAS[nome])


@pytest.mark.parametrize("nome", NOMES)
def test_numero_de_blocos_e_categorias(nome):
    blocos = ESPERADO[nome][2]
    assert len(blocos) == NUMERO_DE_BLOCOS[nome]
    contagem = tuple(sum(b.categoria == c for b in blocos) for c in (AQ, ES, RE, DE, LE))
    assert contagem == CATEGORIAS[nome]


@pytest.mark.parametrize("nome", NOMES)
def test_blocos_cobrem_todas_as_voltas_em_ordem(gerador, nome):
    blocos = ESPERADO[nome][2]
    assert blocos[0].volta_inicial == 0
    for ant, prox in zip(blocos, blocos[1:]):
        assert prox.volta_inicial == ant.volta_final + 1
    assert blocos[-1].volta_final == len(_voltas(gerador, nome)) - 1


@pytest.mark.parametrize("nome", NOMES)
def test_agregados_do_oraculo_batem_com_as_voltas_do_gerador(gerador, nome):
    modalidade = ESPERADO[nome][0]
    voltas = _voltas(gerador, nome)
    for b in ESPERADO[nome][2]:
        grupo = voltas[b.volta_inicial : b.volta_final + 1]
        dist = sum(v[1] for v in grupo)
        dur = sum(v[2] for v in grupo)
        fc = sum(v[2] * v[3] for v in grupo) / dur
        assert dist == pytest.approx(b.distancia_m, abs=1e-9)
        assert dur == pytest.approx(b.duracao_s, abs=1e-9)
        assert fc == pytest.approx(b.fc_media, abs=1e-9)
        esperado = dur / dist * 1000 if modalidade == "corrida" else dist / dur * 3.6
        assert esperado == pytest.approx(b.intensidade, abs=1e-9)
        assert grupo[-1][4] == b.parada_apos_s  # parada depois da última volta do bloco
        assert all(v[4] == 0 for v in grupo[:-1])  # nunca há parada dentro de um bloco juntado


@pytest.mark.parametrize("nome", NOMES)
def test_limiar_de_esforco_da_adr(nome):
    # ADR 0008, item 5: corrida, pace <= ref x 0,90; ciclismo, velocidade >= ref x 1,15.
    modalidade, ref, blocos = ESPERADO[nome]
    for b in blocos:
        if modalidade == "corrida":
            forte = b.intensidade <= ref * 0.90
        else:
            forte = b.intensidade >= ref * 1.15
        assert forte == (b.categoria == ES), b


@pytest.mark.parametrize("nome", NOMES)
def test_categoria_pela_posicao_e_faixa_na_adr(nome):
    blocos = ESPERADO[nome][2]
    idx = [i for i, b in enumerate(blocos) if b.categoria == ES]
    if not idx:  # sem esforço: tudo leve
        assert all(b.categoria == LE for b in blocos)
    else:
        assert all(b.categoria == AQ for b in blocos[: idx[0]])
        assert all(b.categoria == DE for b in blocos[idx[-1] + 1 :])
        assert all(b.categoria == RE for b in blocos[idx[0] : idx[-1] + 1] if b.categoria != ES)
    for b in blocos:
        if b.faixa:  # a medida do bloco (distância na corrida, duração no ciclismo) cai na faixa da ADR
            medida = b.distancia_m if ESPERADO[nome][0] == "corrida" else b.duracao_s
            assert FAIXAS[b.faixa][0] <= medida <= FAIXAS[b.faixa][1]
        assert (b.faixa is not None) <= (b.categoria == ES)  # só esforço tem faixa
        assert b.treino_chave <= (b.categoria == ES)


def test_valores_a_mao_citados_nas_notas():
    # Contas da ADR 0008 e da nota esforcos-oraculo.md.
    assert sum(b.parada_apos_s for b in E1) == 810  # 9 x 90 s de recuperação passiva
    assert sum(b.duracao_s for b in E1 if b.categoria == ES) == 880  # 10 x 88 s
    assert sum(b.distancia_m for b in E1 if b.categoria == ES) == 4000
    assert E2[1].intensidade == pytest.approx(240.6667, abs=1e-4)  # 361 / 1500 x 1000
    assert [b.treino_chave for b in E3] == [True] and 1 - E3[0].intensidade / 330 == pytest.approx(0.1818, abs=1e-4)
    assert [b.treino_chave for b in E1 + E2 + E4 + E5 + E6 + E7] == [False] * (12 + 5 + 1 + 27 + 12 + 3)
    # visão de tiros de 1 km (regressão, caso 4): 5 esforços d1000, pace 250 s/km
    mil = [b for b in E5 if b.faixa == "d1000"]
    assert len(mil) == 5 and sum(b.duracao_s for b in mil) / sum(b.distancia_m for b in mil) * 1000 == 250
    # ciclismo, exemplo 4: 36 km/h x 4 min = 2,4 km
    assert E6[1].distancia_m == 2400 and E6[1].intensidade == 36.0
    assert sum(b.duracao_s for b in E6 if b.categoria == DE) == 120 + 600  # a recuperação final + 10 min


@pytest.mark.parametrize("nome", NOMES)
def test_fit_versionado_bate_com_a_tabela_do_gerador(gerador, nome):
    voltas = _voltas(gerador, nome)
    conteudo = (PASTA_FIT / nome).read_bytes()
    assert conteudo == gerador.montar_fits_esforcos()[nome]  # arquivo versionado = saída do gerador
    fit = ler_fit(conteudo)
    assert de_fit(fit.sport, fit.sub_sport)[0] == ESPERADO[nome][0]
    assert len(fit.voltas) == len(voltas)
    for i, (v, (_intens, dist, dur, fc, parada)) in enumerate(zip(fit.voltas, voltas)):
        assert v.ordem == i
        assert v.distancia_m == pytest.approx(dist, abs=0.01)
        assert v.duracao_s == pytest.approx(dur, abs=1e-3)
        assert v.fc_media == fc
        if i + 1 < len(voltas):
            # tempo parado = intervalo entre os inícios menos a duração em movimento (ADR 0008, item 3)
            parada_lida = fit.voltas[i + 1].inicio_offset_s - v.inicio_offset_s - v.duracao_s
            assert parada_lida == pytest.approx(parada, abs=1e-3)
    assert fit.duracao_s == pytest.approx(sum(v[2] for v in voltas), abs=1e-3)


def test_so_os_arquivos_listados():
    assert {p.name for p in PASTA_FIT.iterdir()} == set(NOMES)
