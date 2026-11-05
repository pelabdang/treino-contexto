"""Blocos do treino: pausas, junção de laps, aquecimento e desaquecimento (issue #162; ADR 0008).

Função pura: sem banco, sem IA. A regra e os limites estão em ``docs/metricas/esforcos.md`` e na ADR 0008
(``docs/decisoes/0008-deteccao-de-esforcos.md``). Qualquer mudança de regra ou de constante exige subir ``VERSAO``
(a versão é gravada junto do resultado e dispara a reclassificação).

Fonte: regra própria do projeto, sem artigo (ADR 0008, "Consequências"). Todos os limites são decisão do projeto,
aprovados pelo Angelo em 04/11, e ficam aqui como constantes nomeadas.

O primeiro passo, comum às modalidades, é ler a sequência de voltas como blocos (``montar_blocos``, #162). Sobre os
blocos, ``esforcos_corrida`` (#163) dá a faixa nomeada de distância (``d200`` a ``d5000``) de cada esforço de corrida.
``esforcos_ciclismo`` (#164) dá a faixa de duração (``t1`` a ``t60``) dos esforços de ciclismo. Treino-chave
contínuo é da #165 e não é calculado aqui.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

VERSAO = "esforcos@1"

MODALIDADE_CORRIDA = "corrida"
MODALIDADE_CICLISMO = "ciclismo"

# Item 2 da ADR: tempo parado entre duas voltas que as separa (menor que isto junta).
PAUSA_SEPARA_S_CORRIDA = 15.0
PAUSA_SEPARA_S_CICLISMO = 30.0  # semáforo e cruzamento são comuns
# Item 2: o ritmo da volta precisa ficar a até 5% do ritmo do bloco acumulado (pace na corrida, velocidade no ciclismo).
JUNTAR_TOLERANCIA = 0.05
# Item 3: volta de pausa (parado ou andando) quando o relógio não pausou sozinho.
PAUSA_PACE_S_KM = 600.0  # corrida: pace maior que isto
PAUSA_DIST_MIN_M = 50.0  # corrida: distância menor que isto
PAUSA_VEL_KMH = 5.0  # ciclismo: velocidade menor que isto
# Item 5: esforço = pace <= ref x (1 - 0,10) na corrida; velocidade >= ref x (1 + 0,15) no ciclismo.
ESFORCO_GANHO_CORRIDA = 0.10
ESFORCO_GANHO_CICLISMO = 0.15

AQUECIMENTO = "aquecimento"
ESFORCO = "esforco"
RECUPERACAO = "recuperacao"
DESAQUECIMENTO = "desaquecimento"
LEVE = "leve"
CATEGORIAS = (ESFORCO, RECUPERACAO, AQUECIMENTO, DESAQUECIMENTO, LEVE)

REF_HABITUAL = "habitual"  # referência vinda do histórico do atleta
REF_ATIVIDADE = "atividade"  # reserva: mediana ponderada dos blocos da própria atividade

_EPS = 1e-9  # os limites são inclusivos; evita que o erro de ponto flutuante tire um valor exato do limite


@dataclass(frozen=True)
class VoltaTreino:
    """Uma volta como o banco a guarda (``segmento``). ``duracao_s`` é o tempo em movimento."""

    ordem: int
    inicio_offset_s: float  # tempo corrido desde o início da atividade
    duracao_s: float
    distancia_m: float
    fc_media: float | None = None
    intensidade: str | None = None  # dica do FIT; não muda a categoria nesta versão


@dataclass(frozen=True)
class BlocoTreino:
    ordem: int  # posição do bloco, a partir de 0
    categoria: str
    volta_inicial: int  # VoltaTreino.ordem da primeira volta
    volta_final: int  # VoltaTreino.ordem da última volta (voltas contíguas, sem pausa no meio)
    inicio_offset_s: float
    duracao_s: float  # tempo em movimento (soma)
    parada_apos_s: float  # tempo parado até o bloco seguinte; 0 no último
    distancia_m: float
    fc_media: float | None  # ponderada pela duração, só sobre voltas com FC
    pace_s_km: float  # duracao / distancia x 1000
    velocidade_kmh: float  # distancia / duracao x 3,6


@dataclass(frozen=True)
class ResultadoBlocos:
    blocos: tuple[BlocoTreino, ...]
    referencia: float | None  # ritmo habitual (s/km) ou velocidade habitual (km/h) usado; None sem blocos
    ref_origem: Literal["habitual", "atividade"] | None
    versao: str = VERSAO


def _pace(distancia_m: float, duracao_s: float) -> float | None:
    if distancia_m <= 0 or duracao_s <= 0:
        return None
    return duracao_s / distancia_m * 1000.0


def _velocidade(distancia_m: float, duracao_s: float) -> float | None:
    if distancia_m <= 0 or duracao_s <= 0:
        return None
    return distancia_m / duracao_s * 3.6


def _pausa_separa_s(modalidade: str) -> float:
    return PAUSA_SEPARA_S_CICLISMO if modalidade == MODALIDADE_CICLISMO else PAUSA_SEPARA_S_CORRIDA


def tempos_parados(voltas: Sequence[VoltaTreino]) -> list[float]:
    """Tempo parado depois de cada volta (item 3): (início da próxima - início desta) - duração, mínimo 0.

    A última volta não tem próxima: 0. Sem ``start_time`` no FIT todos os inícios são 0 e a conta dá 0.
    """
    paradas = []
    for i, v in enumerate(voltas):
        if i + 1 < len(voltas):
            paradas.append(max(0.0, voltas[i + 1].inicio_offset_s - v.inicio_offset_s - v.duracao_s))
        else:
            paradas.append(0.0)
    return paradas


def eh_volta_de_pausa(volta: VoltaTreino, modalidade: str) -> bool:
    """Volta parada ou muito curta (item 3): o atleta parou e o relógio não pausou sozinho."""
    pace = _pace(volta.distancia_m, volta.duracao_s)
    vel = _velocidade(volta.distancia_m, volta.duracao_s)
    if pace is None or vel is None:
        return True
    if modalidade == MODALIDADE_CICLISMO:
        return vel < PAUSA_VEL_KMH
    return pace > PAUSA_PACE_S_KM or volta.distancia_m < PAUSA_DIST_MIN_M


def _ritmo_parecido(volta: VoltaTreino, dist_bloco: float, dur_bloco: float, modalidade: str) -> bool:
    """Ritmo da volta a até ``JUNTAR_TOLERANCIA`` do ritmo do bloco acumulado (ponderado por distância)."""
    if modalidade == MODALIDADE_CICLISMO:
        v, ref = _velocidade(volta.distancia_m, volta.duracao_s), _velocidade(dist_bloco, dur_bloco)
    else:
        v, ref = _pace(volta.distancia_m, volta.duracao_s), _pace(dist_bloco, dur_bloco)
    if v is None or ref is None:
        return False
    return abs(v - ref) / ref <= JUNTAR_TOLERANCIA + _EPS


def _agregar(voltas: Sequence[VoltaTreino]) -> tuple[float, float, float | None]:
    dist = sum(v.distancia_m for v in voltas)
    dur = sum(v.duracao_s for v in voltas)
    com_fc = [v for v in voltas if v.fc_media is not None]
    dur_fc = sum(v.duracao_s for v in com_fc)
    fc = sum(v.fc_media * v.duracao_s for v in com_fc) / dur_fc if dur_fc > 0 else None
    return dist, dur, fc


def _mediana_ponderada(valores_e_pesos: list[tuple[float, float]]) -> float:
    """Menor valor cujo peso acumulado chega à metade do peso total."""
    ordenado = sorted(valores_e_pesos)
    total = sum(p for _, p in ordenado)
    acumulado = 0.0
    for valor, peso in ordenado:
        acumulado += peso
        if acumulado >= total / 2 - _EPS:
            return valor
    return ordenado[-1][0]


def _eh_esforco(bloco: BlocoTreino, referencia: float, modalidade: str) -> bool:
    if modalidade == MODALIDADE_CICLISMO:
        return bloco.velocidade_kmh >= referencia * (1 + ESFORCO_GANHO_CICLISMO) - _EPS
    return bloco.pace_s_km <= referencia * (1 - ESFORCO_GANHO_CORRIDA) + _EPS


def montar_blocos(
    voltas: Sequence[VoltaTreino],
    modalidade: str,
    referencia: float | None = None,
) -> ResultadoBlocos:
    """Lê as voltas de uma atividade como blocos (ADR 0008, itens 1 a 5).

    1. Volta de pausa (parada ou muito curta) não é bloco: separa os blocos e o tempo dela entra em
       ``parada_apos_s`` do bloco anterior, junto do tempo parado entre as voltas.
    2. Voltas consecutivas se juntam quando o tempo parado entre elas é menor que a pausa que separa e o ritmo da
       volta fica a até 5% do ritmo do bloco acumulado.
    3. ``referencia`` é o ritmo habitual (s/km, corrida) ou a velocidade habitual (km/h, ciclismo). Sem ela, vale a
       mediana, ponderada pela duração, dos blocos da própria atividade (``ref_origem = "atividade"``).
    4. Esforço = ritmo melhor que o limiar da ADR. Com esforço: antes do primeiro, aquecimento; depois do último,
       desaquecimento; entre eles, recuperação. Sem esforço, todos os blocos são leves.

    Só ``corrida`` e ``ciclismo``; outra modalidade devolve zero blocos. O tempo parado antes do primeiro bloco e
    depois do último é ignorado (não há bloco do outro lado).
    """
    if modalidade not in (MODALIDADE_CORRIDA, MODALIDADE_CICLISMO):
        return ResultadoBlocos((), None, None)
    ordenadas = sorted(voltas, key=lambda v: v.ordem)
    paradas = tempos_parados(ordenadas)
    separa_s = _pausa_separa_s(modalidade)

    # 1 e 2: grupos de voltas; cada grupo guarda a parada que o segue.
    grupos: list[list[VoltaTreino]] = []
    parada_apos: list[float] = []
    anterior_fechou = True  # True: a próxima volta abre um grupo novo
    for v, parada in zip(ordenadas, paradas):
        if eh_volta_de_pausa(v, modalidade):
            if grupos:
                parada_apos[-1] += v.duracao_s + parada
            anterior_fechou = True
            continue
        if not anterior_fechou:
            atual = grupos[-1]
            dist, dur, _ = _agregar(atual)
            if parada_apos[-1] < separa_s - _EPS and _ritmo_parecido(v, dist, dur, modalidade):
                atual.append(v)
                parada_apos[-1] = parada
                continue
        grupos.append([v])
        parada_apos.append(parada)
        anterior_fechou = False

    brutos = []
    for i, g in enumerate(grupos):
        dist, dur, fc = _agregar(g)
        brutos.append(
            (g, dist, dur, fc, parada_apos[i] if i + 1 < len(grupos) else 0.0)
        )
    if not brutos:
        return ResultadoBlocos((), None, None)

    # 3: referência
    medidas = [
        (_velocidade(d, t) if modalidade == MODALIDADE_CICLISMO else _pace(d, t), t) for _, d, t, _, _ in brutos
    ]
    if referencia is not None:
        ref, origem = referencia, REF_HABITUAL
    else:
        ref, origem = _mediana_ponderada([(m, t) for m, t in medidas]), REF_ATIVIDADE

    # 4: categorias
    previos = [
        BlocoTreino(
            ordem=i,
            categoria=LEVE,
            volta_inicial=g[0].ordem,
            volta_final=g[-1].ordem,
            inicio_offset_s=g[0].inicio_offset_s,
            duracao_s=dur,
            parada_apos_s=parada,
            distancia_m=dist,
            fc_media=fc,
            pace_s_km=_pace(dist, dur),
            velocidade_kmh=_velocidade(dist, dur),
        )
        for i, (g, dist, dur, fc, parada) in enumerate(brutos)
    ]
    esforcos = [i for i, b in enumerate(previos) if _eh_esforco(b, ref, modalidade)]
    blocos = []
    for i, b in enumerate(previos):
        if not esforcos:
            cat = LEVE
        elif i in esforcos:
            cat = ESFORCO
        elif i < esforcos[0]:
            cat = AQUECIMENTO
        elif i > esforcos[-1]:
            cat = DESAQUECIMENTO
        else:
            cat = RECUPERACAO
        blocos.append(BlocoTreino(**{**b.__dict__, "categoria": cat}))
    return ResultadoBlocos(tuple(blocos), ref, origem)


# --- Esforços de corrida por distância (issue #163; ADR 0008, item 5) -------------------------------------------
# Faixas nomeadas (alvo em metros): tolerância max(5% do alvo, 30 m) para cada lado, inclusiva nos dois extremos.
# Fonte: regra própria do projeto, sem artigo (ADR 0008, "Consequências"). Os limites estão escritos como a ADR os
# lista (inteiros), para não depender de arredondamento de ponto flutuante; o teste confere cada um com a fórmula.
FAIXA_TOLERANCIA_PCT = 0.05
FAIXA_TOLERANCIA_MIN_M = 30.0
FAIXAS_CORRIDA: tuple[tuple[str, float, float], ...] = (
    ("d200", 170.0, 230.0),
    ("d300", 270.0, 330.0),
    ("d400", 370.0, 430.0),
    ("d500", 470.0, 530.0),
    ("d600", 570.0, 630.0),
    ("d800", 760.0, 840.0),
    ("d1000", 950.0, 1050.0),
    ("d1200", 1140.0, 1260.0),
    ("d1500", 1425.0, 1575.0),
    ("d2000", 1900.0, 2100.0),
    ("d3000", 2850.0, 3150.0),
    ("d5000", 4750.0, 5250.0),
)


@dataclass(frozen=True)
class EsforcoCorrida:
    """Um bloco de esforço da corrida com a faixa de distância a que pertence (``faixa`` é None fora de todas)."""

    bloco_ordem: int
    faixa: str | None
    volta_inicial: int
    volta_final: int
    inicio_offset_s: float
    distancia_m: float
    duracao_s: float
    pace_s_km: float
    fc_media: float | None
    parada_apos_s: float


def faixa_de_distancia(distancia_m: float) -> str | None:
    """Nome da faixa de corrida que contém a distância, ou None (esforço entre faixas ou fora delas).

    Limites inclusivos. As faixas da ADR não se sobrepõem, então há no máximo uma. Distância entre duas faixas
    (por exemplo 700 m ou 1350 m) não tem faixa: o esforço continua esforço, com a distância real (ADR, item 5).
    """
    for nome, minimo, maximo in FAIXAS_CORRIDA:
        if minimo - _EPS <= distancia_m <= maximo + _EPS:
            return nome
    return None


def esforcos_corrida(resultado: ResultadoBlocos) -> tuple[EsforcoCorrida, ...]:
    """Esforços de uma corrida, na ordem, com a faixa de distância de cada um (ADR 0008, item 5).

    Recebe o resultado de ``montar_blocos(..., "corrida")``: só os blocos de categoria ``esforco`` entram; a junção
    de laps (1000 m + 500 m = 1500 m) já veio dos blocos. A faixa vem da distância do bloco inteiro. Pace e FC são
    os do bloco (pace = duração / distância x 1000; FC ponderada pela duração).
    """
    return tuple(
        EsforcoCorrida(
            bloco_ordem=b.ordem,
            faixa=faixa_de_distancia(b.distancia_m),
            volta_inicial=b.volta_inicial,
            volta_final=b.volta_final,
            inicio_offset_s=b.inicio_offset_s,
            distancia_m=b.distancia_m,
            duracao_s=b.duracao_s,
            pace_s_km=b.pace_s_km,
            fc_media=b.fc_media,
            parada_apos_s=b.parada_apos_s,
        )
        for b in resultado.blocos
        if b.categoria == ESFORCO
    )


# --- Esforços de ciclismo por duração (issue #164; ADR 0008, item 5) -------------------------------------------
# Faixas nomeadas (alvo em minutos): tolerância max(8% do alvo, 15 s) para cada lado, inclusiva, sobre a duração em
# movimento do bloco. Fonte: regra própria do projeto, sem artigo. Os limites são os inteiros da ADR (aprovados pelo
# Angelo em 04/11), que arredonda ao segundo mais próximo (ex.: t12, 720 +- 57,6 = 662,4 a 777,6 -> 662 a 778).
FAIXA_TOLERANCIA_CICLISMO_PCT = 0.08
FAIXA_TOLERANCIA_CICLISMO_MIN_S = 15.0
FAIXAS_CICLISMO: tuple[tuple[str, float, float], ...] = (
    ("t1", 45.0, 75.0),
    ("t2", 105.0, 135.0),
    ("t3", 165.0, 195.0),
    ("t4", 221.0, 259.0),
    ("t5", 276.0, 324.0),
    ("t8", 442.0, 518.0),
    ("t10", 552.0, 648.0),
    ("t12", 662.0, 778.0),
    ("t15", 828.0, 972.0),
    ("t20", 1104.0, 1296.0),
    ("t30", 1656.0, 1944.0),
    ("t40", 2208.0, 2592.0),
    ("t60", 3312.0, 3888.0),
)


@dataclass(frozen=True)
class EsforcoCiclismo:
    """Um bloco de esforço do ciclismo com a faixa de duração (``faixa`` é None fora de todas)."""

    bloco_ordem: int
    faixa: str | None
    volta_inicial: int
    volta_final: int
    inicio_offset_s: float
    duracao_s: float
    distancia_m: float
    velocidade_kmh: float
    fc_media: float | None
    parada_apos_s: float


def faixa_de_duracao(duracao_s: float) -> str | None:
    """Faixa de ciclismo que contém a duração em movimento, ou None. Limites inclusivos, sem sobreposição."""
    for nome, minimo, maximo in FAIXAS_CICLISMO:
        if minimo - _EPS <= duracao_s <= maximo + _EPS:
            return nome
    return None


def esforcos_ciclismo(resultado: ResultadoBlocos) -> tuple[EsforcoCiclismo, ...]:
    """Esforços de um pedal, na ordem, com a faixa de duração (ADR 0008, item 5).

    Recebe ``montar_blocos(..., "ciclismo")``: só os blocos de categoria ``esforco`` entram (aquecimento,
    recuperação e desaquecimento ficam de fora). A junção de laps já veio dos blocos. Sem potência: a intensidade
    é a velocidade contra a habitual (limitação de relevo e vento na nota da métrica).
    """
    return tuple(
        EsforcoCiclismo(
            bloco_ordem=b.ordem,
            faixa=faixa_de_duracao(b.duracao_s),
            volta_inicial=b.volta_inicial,
            volta_final=b.volta_final,
            inicio_offset_s=b.inicio_offset_s,
            duracao_s=b.duracao_s,
            distancia_m=b.distancia_m,
            velocidade_kmh=b.velocidade_kmh,
            fc_media=b.fc_media,
            parada_apos_s=b.parada_apos_s,
        )
        for b in resultado.blocos
        if b.categoria == ESFORCO
    )
