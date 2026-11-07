"""Tiros de 1 km: visão sobre os esforços (issue #168, ADR 0008 item 8) e agregação por sessão (issue #12).

Funções puras: sem banco, sem IA. A regra completa e os limites estão em
docs/metricas/tiros-1km.md. Qualquer mudança de regra ou de constante exige
subir ``VERSAO`` (a versão é gravada junto do resultado).

Fonte: regra própria do projeto (não há artigo). Desde a ``tiros_1km@5`` a série não lê mais voltas: lê os
**blocos** que ``app.metricas.esforcos`` (``esforcos@1``) já separou em aquecimento, esforço, recuperação e
desaquecimento. Um tiro de 1 km é um bloco ``esforco`` da faixa ``d1000`` (950 a 1050 m) que não é continuação de
um progressivo ou fartlek. Os limites de 20% (ritmo parecido), 15% (bloco contínuo) e 10% (ritmo habitual) são
decisão do projeto.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from app.metricas import esforcos as ef

VERSAO = "tiros_1km@6"

# Faixa de esforço de corrida que vale como tiro de 1 km (ADR 0008, item 5): 950 a 1050 m. Um esforço de 1500 m
# (``d1500``) ou de 2000 m (dois km seguidos no mesmo ritmo) não é tiro de 1 km.
FAIXA_TIRO = "d1000"
# Sessão com pelo menos 2 tiros entra na série (decisão do Angelo, 04/11; era 3 até a @4).
MIN_TIROS_INTERVALADO = 2
# O ritmo parecido (abaixo) só olha sessões com 3 ou mais tiros: com 2, a mediana é a média dos dois e não diz nada.
MIN_TIROS_RITMO_PARECIDO = 3
# Bloco vizinho "de corrida" para o teste do bloco contínuo: pelo menos 950 m (um km, ou vários km juntados).
VIZINHO_MIN_M = 950.0

MODALIDADE_CORRIDA = "corrida"

# @6: pausa dentro do tiro. Um tiro cortado por uma parada (semáforo, bebida, cronômetro parado) chega dos esforços
# como 2 ou 3 pedaços separados; os pedaços de esforço vizinhos, de ritmo parecido (5%, ``JUNTAR_TOLERANCIA`` dos
# esforços), com parada menor que isto entre eles e somando 950 a 1050 m, valem como um tiro só, que conta o tempo
# em movimento. Parada de ``PAUSA_NO_TIRO_MAX_S`` ou mais é descanso de série e continua separando. Decisão do
# projeto (proposta do Caio, a aprovar; ADR 0008, adendo), não vem de artigo.
PAUSA_NO_TIRO_MAX_S = 60.0
PEDACOS_TIRO_MIN = 2
PEDACOS_TIRO_MAX = 3

# Ritmo habitual do atleta (@3): mediana do pace das corridas de mais de 3 km (sem esteira),
# anteriores à sessão, nas últimas 12 semanas; com menos de 10 na janela, todo o histórico.
HABITUAL_DISTANCIA_MIN_M = 3000.0
HABITUAL_JANELA_DIAS = 84
HABITUAL_MIN_CORRIDAS_JANELA = 10
# Os tiros da sessão precisam ter pace médio pelo menos 10% mais rápido que o ritmo habitual
# (@4; era 5% na @3).
HABITUAL_GANHO_MINIMO = 0.10

# @4, ritmo parecido: com 3 ou mais tiros, um tiro mais de 20% mais lento que a mediana dos
# tiros da sessão não é tiro (desaquecimento de 1 km que virou esforço por estar abaixo do ritmo habitual).
RITMO_PARECIDO_TOLERANCIA = 0.20
# @4, bloco contínuo: um bloco de corrida ao lado do tiro, que seja menos de 15% mais lento que ele, indica
# progressivo ou fartlek, não tiro.
BLOCO_CONTINUO_GANHO_MINIMO = 0.15


@dataclass(frozen=True)
class VoltaEntrada:
    """Um tiro como a agregação o recebe: ``ordem`` é a ``segmento.ordem`` da primeira volta do bloco."""

    ordem: int
    distancia_m: float
    duracao_s: float
    fc_media: float | None = None
    intensidade: str | None = None  # só informativa; a regra não usa


@dataclass(frozen=True)
class BlocoEntrada:
    """Um bloco como ``bloco_atividade`` o guarda (ADR 0008, item 9), só com o que a visão usa."""

    ordem: int
    categoria: str
    volta_inicial: int
    volta_final: int
    distancia_m: float | None
    duracao_s: float
    fc_media: float | None = None
    faixa: str | None = None
    parada_apos_s: float | None = None


@dataclass(frozen=True)
class ResultadoTiros:
    tiros: tuple[int, ...]  # ``ordem`` dos blocos que são tiros
    recuperacoes: tuple[int, ...]  # ``ordem`` dos blocos não-tiro entre o primeiro e o último tiro
    eh_intervalado: bool
    versao: str = VERSAO
    # Os tiros como blocos (``ordem`` = a do primeiro pedaço), já com os pedaços cortados por pausa juntados (@6).
    # Quem precisa de distância, duração ou voltas de cada tiro lê daqui, não da lista original de blocos.
    blocos_tiro: tuple[BlocoEntrada, ...] = ()


def _pace_s_km(b: BlocoEntrada) -> float | None:
    if not b.distancia_m or b.distancia_m <= 0 or b.duracao_s <= 0:
        return None
    return b.duracao_s / b.distancia_m * 1000.0


def _vizinho_corta(blocos: list[BlocoEntrada], i: int, candidatos: set[int]) -> bool:
    """O tiro ``blocos[i]`` é continuação de um bloco de corrida vizinho (progressivo, fartlek)?

    Olha o bloco anterior e o seguinte. Um vizinho conta quando tem pelo menos 950 m, não é aquecimento nem
    desaquecimento e o tiro é menos de 15% mais rápido que ele (``pace do tiro > pace do vizinho x 0,85``; vizinho
    mais lento que isso deixa o tiro de pé). Fica de fora o vizinho que é ele mesmo um tiro candidato **separado
    por uma pausa** (parada de pelo menos 15 s): são repetições com descanso parado, não bloco contínuo.
    """
    pace = _pace_s_km(blocos[i])
    for j in (i - 1, i + 1):
        if not 0 <= j < len(blocos):
            continue
        viz = blocos[j]
        if viz.categoria in (ef.AQUECIMENTO, ef.DESAQUECIMENTO):
            continue
        if (viz.distancia_m or 0.0) < VIZINHO_MIN_M:
            continue
        pace_viz = _pace_s_km(viz)
        if pace_viz is None:
            continue
        parada = (blocos[min(i, j)].parada_apos_s or 0.0)
        if viz.ordem in candidatos and parada >= ef.PAUSA_SEPARA_S_CORRIDA - 1e-9:
            continue
        if pace > pace_viz * (1.0 - BLOCO_CONTINUO_GANHO_MINIMO):
            return True
    return False


def _juntar_pedacos(blocos: list[BlocoEntrada]) -> list[BlocoEntrada]:
    """@6: junta os pedaços de um tiro de 1 km que uma pausa cortou (ver ``PAUSA_NO_TIRO_MAX_S``).

    Cadeia = esforços de menos de 950 m, consecutivos na ordem dos blocos (nenhuma recuperação entre eles), cada um
    separado do seguinte por parada menor que o limite. Só uma cadeia de 2 ou 3 pedaços, de ritmo parecido (cada
    pedaço a até 5% do pace acumulado) e somando 950 a 1050 m vira um bloco. Cadeia maior é série de repetições
    curtas com descanso curto (8 x 500 m com 30 s, por exemplo), não um tiro cortado: não se junta.
    """
    resultado: list[BlocoEntrada] = []
    i = 0
    while i < len(blocos):
        cadeia = [blocos[i]]
        if blocos[i].categoria == ef.ESFORCO and (blocos[i].distancia_m or 0.0) < VIZINHO_MIN_M:
            while i + len(cadeia) < len(blocos):
                ult, prox = cadeia[-1], blocos[i + len(cadeia)]
                if (
                    prox.categoria != ef.ESFORCO
                    or (prox.distancia_m or 0.0) >= VIZINHO_MIN_M
                    or (ult.parada_apos_s or 0.0) >= PAUSA_NO_TIRO_MAX_S - 1e-9
                ):
                    break
                cadeia.append(prox)
        junto = _bloco_de_pedacos(cadeia) if PEDACOS_TIRO_MIN <= len(cadeia) <= PEDACOS_TIRO_MAX else None
        if junto is not None:
            resultado.append(junto)
        else:
            resultado.extend(cadeia)
        i += len(cadeia)
    return resultado


def _bloco_de_pedacos(cadeia: list[BlocoEntrada]) -> BlocoEntrada | None:
    """O bloco de 1 km que os pedaços formam, ou ``None`` se a soma não cai na faixa ou o ritmo não é parecido."""
    dist = dur = 0.0
    for b in cadeia:
        pace_b = _pace_s_km(b)
        if pace_b is None:
            return None
        if dist > 0 and abs(pace_b - dur / dist * 1000.0) / (dur / dist * 1000.0) > ef.JUNTAR_TOLERANCIA + 1e-9:
            return None
        dist += b.distancia_m or 0.0
        dur += b.duracao_s
    if ef.faixa_de_distancia(dist) != FAIXA_TIRO:
        return None
    com_fc = [b for b in cadeia if b.fc_media is not None]
    dur_fc = sum(b.duracao_s for b in com_fc)
    fc = sum(b.fc_media * b.duracao_s for b in com_fc) / dur_fc if dur_fc > 0 else None  # type: ignore[operator]
    primeiro, ultimo = cadeia[0], cadeia[-1]
    return BlocoEntrada(
        primeiro.ordem, ef.ESFORCO, primeiro.volta_inicial, ultimo.volta_final, dist, dur, fc, FAIXA_TIRO,
        ultimo.parada_apos_s,
    )  # fmt: skip


def tiros_de_blocos(blocos: Sequence[BlocoEntrada], modalidade: str = MODALIDADE_CORRIDA) -> ResultadoTiros:
    """Os tiros de 1 km de uma atividade, lidos dos blocos (``esforcos@1``).

    1. Candidato: bloco de categoria ``esforco`` e faixa ``d1000``. Aquecimento, desaquecimento, recuperação e
       rodagem (``leve``) ficam de fora pela própria categoria; um esforço de 1500 m ou de 2000 m, também.
    2. Ritmo parecido: com 3 ou mais candidatos, sai o mais de 20% mais lento que a mediana deles.
    0. (@6) Pedaços de esforço cortados por uma pausa curta valem como um bloco só (``_juntar_pedacos``).
    3. Bloco contínuo: sai o candidato que é menos de 15% mais rápido que um bloco vizinho de corrida (ver
       ``_vizinho_corta``).
    4. ``eh_intervalado`` = pelo menos 2 tiros. Sem o volume do bloco principal da @4: o aquecimento e o
       desaquecimento já saem por categoria, e os esforços curtos (``d400`` etc.) simplesmente não são de 1 km.
    """
    if modalidade != MODALIDADE_CORRIDA or not blocos:
        return ResultadoTiros((), (), False)
    blocos = _juntar_pedacos(sorted(blocos, key=lambda b: b.ordem))
    cand = [b for b in blocos if b.categoria == ef.ESFORCO and b.faixa == FAIXA_TIRO and _pace_s_km(b) is not None]

    if len(cand) >= MIN_TIROS_RITMO_PARECIDO:
        mediana = median(_pace_s_km(b) for b in cand)
        cand = [b for b in cand if _pace_s_km(b) <= mediana * (1.0 + RITMO_PARECIDO_TOLERANCIA)]

    posicao = {b.ordem: i for i, b in enumerate(blocos)}
    ordens_cand = {b.ordem for b in cand}
    tiros = [b for b in cand if not _vizinho_corta(blocos, posicao[b.ordem], ordens_cand)]

    ordens = tuple(b.ordem for b in tiros)
    recuperacoes: tuple[int, ...] = ()
    if len(ordens) >= 2:
        recuperacoes = tuple(b.ordem for b in blocos if ordens[0] < b.ordem < ordens[-1] and b.ordem not in ordens)
    return ResultadoTiros(ordens, recuperacoes, len(ordens) >= MIN_TIROS_INTERVALADO, VERSAO, tuple(tiros))


def tiro_de_bloco(b: BlocoEntrada) -> VoltaEntrada:
    """O bloco de um tiro no formato da agregação (``ordem`` = primeira volta do bloco)."""
    return VoltaEntrada(b.volta_inicial, b.distancia_m or 0.0, b.duracao_s, b.fc_media)


# ---------------------------------------------------------------------------
# Agregação por sessão (issue #12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessaoTiros:
    """Uma atividade já classificada: os tiros e se é intervalado."""

    atividade_id: int | str
    data: date  # data local do início da atividade
    eh_intervalado: bool
    tiros: tuple[VoltaEntrada, ...]
    versao: str = VERSAO


@dataclass(frozen=True)
class PontoSessao:
    """Um ponto da série: valores sem arredondar (ver ``para_apresentacao``)."""

    atividade_id: int | str
    data: date
    n_tiros: int
    pace_s_km: float
    fc_media: float | None
    # Melhor tiro (#151): o de menor pace; empate = o primeiro na ordem dada.
    # Sempre preenchidos por ``agregar_sessao``; o default None só mantém compatível quem monta
    # o ponto à mão (testes do gráfico) até a #152 levar o melhor tiro ao contrato.
    melhor_pace_s_km: float | None = None
    melhor_fc_media: float | None = None  # FC dele; None se ele não tem FC (não troca de tiro)
    melhor_ordem: int | None = None  # ordem da volta do melhor tiro
    versao: str = VERSAO


def sessao_de_blocos(
    atividade_id: int | str,
    data: date,
    blocos: Sequence[BlocoEntrada],
    modalidade: str = MODALIDADE_CORRIDA,
) -> SessaoTiros:
    """Detecta os tiros nos blocos (#168) e monta a sessão pronta para agregar."""
    resultado = tiros_de_blocos(blocos, modalidade)
    tiros = tuple(tiro_de_bloco(b) for b in resultado.blocos_tiro)
    return SessaoTiros(atividade_id, data, resultado.eh_intervalado, tiros, resultado.versao)


def agregar_sessao(
    atividade_id: int | str,
    data: date,
    tiros: list[VoltaEntrada] | tuple[VoltaEntrada, ...],
    versao: str = VERSAO,
) -> PontoSessao:
    """Pace e FC médios dos tiros de uma sessão.

    pace (s/km) = soma das durações / soma das distâncias x 1000. É a média
    ponderada pela distância dos paces, e não a média simples deles (que
    erraria quando os tiros têm distâncias diferentes: 1000 m e 990 m).

    FC (bpm) = soma(FC x duração) / soma(duração), só sobre tiros com FC.
    Sem nenhuma FC, ``None``. Fonte: média ponderada simples (definição
    combinada na issue #12); sem arredondamento aqui.

    Melhor tiro (#151): o de menor pace (duração / distância x 1000), com a FC
    dele. Empate: o primeiro da sequência recebida (``min`` devolve o primeiro
    mínimo). Se o melhor tiro não tem FC, ``melhor_fc_media`` é ``None``: não
    se troca por outro tiro. Regra própria do projeto, sem artigo.
    """
    if not tiros:
        raise ValueError("sessão sem tiros não tem agregação")
    dur_total = sum(t.duracao_s for t in tiros)
    dist_total = sum(t.distancia_m for t in tiros)
    if dist_total <= 0:
        raise ValueError("soma das distâncias dos tiros deve ser positiva")
    pace = dur_total / dist_total * 1000.0

    com_fc = [t for t in tiros if t.fc_media is not None]
    dur_fc = sum(t.duracao_s for t in com_fc)
    fc = (
        sum(t.fc_media * t.duracao_s for t in com_fc) / dur_fc  # type: ignore[operator]
        if com_fc and dur_fc > 0
        else None
    )
    # tiro sem distância não tem pace: fora da escolha (dist_total > 0 garante ao menos um)
    melhor = min((t for t in tiros if t.distancia_m > 0), key=lambda t: t.duracao_s / t.distancia_m)
    return PontoSessao(
        atividade_id,
        data,
        len(tiros),
        pace,
        fc,
        melhor.duracao_s / melhor.distancia_m * 1000.0,
        melhor.fc_media,
        melhor.ordem,
        versao,
    )


def serie_por_sessao(sessoes: list[SessaoTiros]) -> list[PontoSessao]:
    """Um ponto por sessão intervalada, ordenado por data (e id, no empate)."""
    pontos = [
        agregar_sessao(s.atividade_id, s.data, s.tiros, s.versao)
        for s in sessoes
        if s.eh_intervalado and s.tiros
    ]
    return sorted(pontos, key=lambda p: (p.data, str(p.atividade_id)))


def para_apresentacao(valor: float | None) -> float | None:
    """Arredonda para 1 casa decimal. Só para mostrar; nunca usar no cálculo."""
    return None if valor is None else round(valor, 1)


def formatar_pace(s_km: float) -> str:
    """Pace em ``m:ss``: arredonda ao segundo, com meio para cima.

    Regra única de ``m:ss`` do projeto (eixo do gráfico, CSV e JSON). Não usa
    ``round()``, que arredonda 0,5 para o par (239,5 -> 240 mas 238,5 -> 238).
    Arredonda os segundos totais antes de separar minutos, então nunca sai "3:60".
    """
    total = math.floor(s_km + 0.5)
    minutos, segundos = divmod(total, 60)
    return f"{minutos}:{segundos:02d}"


# ---------------------------------------------------------------------------
# Ritmo habitual do atleta (issue #53, tiros_1km@3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorridaHistorico:
    """Uma corrida do atleta, só com o que o ritmo habitual usa."""

    data: date  # data local do início
    distancia_m: float
    duracao_s: float
    esteira: bool = False


def pace_habitual(historico: Iterable[CorridaHistorico], data_sessao: date) -> float | None:
    """Ritmo habitual do atleta (s/km) antes de ``data_sessao``, ou ``None`` sem histórico.

    Mediana do pace (duração / distância x 1000) das corridas de mais de 3 km, sem esteira,
    com data anterior à da sessão, nos 84 dias (12 semanas) antes dela. Com menos de 10
    corridas nessa janela, usa todo o histórico anterior. Mediana porque não é puxada pelas
    poucas sessões de tiros nem por uma corrida atípica. Sem nenhuma corrida anterior, devolve
    ``None`` e quem chama não filtra.
    """
    anteriores = [
        c.duracao_s / c.distancia_m * 1000.0
        for c in historico
        if c.data < data_sessao
        and not c.esteira
        and c.distancia_m > HABITUAL_DISTANCIA_MIN_M
        and c.duracao_s > 0
    ]
    if not anteriores:
        return None
    inicio_janela = data_sessao - timedelta(days=HABITUAL_JANELA_DIAS)
    na_janela = [
        c.duracao_s / c.distancia_m * 1000.0
        for c in historico
        if inicio_janela <= c.data < data_sessao
        and not c.esteira
        and c.distancia_m > HABITUAL_DISTANCIA_MIN_M
        and c.duracao_s > 0
    ]
    base = na_janela if len(na_janela) >= HABITUAL_MIN_CORRIDAS_JANELA else anteriores
    return median(base)


def mais_rapido_que_o_habitual(pace_tiros_s_km: float, habitual_s_km: float | None) -> bool:
    """Os tiros são pelo menos 10% mais rápidos que o ritmo habitual?

    ``pace_tiros <= habitual x 0,90``, sem arredondar; o limite exato entra. Sem ritmo
    habitual (``None``) não há filtro: devolve verdadeiro.
    """
    if habitual_s_km is None:
        return True
    return pace_tiros_s_km <= habitual_s_km * (1.0 - HABITUAL_GANHO_MINIMO)
