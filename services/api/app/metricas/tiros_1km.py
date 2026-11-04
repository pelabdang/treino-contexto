"""Tiros de 1 km: detecção (issues #11 e #48) e agregação por sessão (issue #12).

Funções puras: sem banco, sem IA. A regra completa e os limites estão em
docs/metricas/tiros-1km.md. Qualquer mudança de regra ou de constante exige
subir ``VERSAO`` (a versão é gravada junto do resultado).

Fonte: regra própria do projeto (não há artigo). Um tiro de 1 km é uma volta
de ~1 km mais rápida que as voltas vizinhas e separada delas por recuperação,
isto é, a estrutura "esforço, pausa, esforço" de um treino intervalado. O
limiar de 8% de pace é decisão do projeto.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Iterable
from datetime import date, timedelta
from statistics import median

VERSAO = "tiros_1km@4"

DISTANCIA_ALVO_M = 1000.0
# Tolerância de GPS/auto-lap: volta de 950 a 1050 m (inclusive) é candidata.
TOLERANCIA_M = 50.0
# Um tiro precisa ser pelo menos 8% mais rápido que a volta vizinha de recuperação.
GANHO_MINIMO_PACE = 0.08
# Volta vizinha mais curta que isto é pausa (parado/andando): sem comparação de pace.
PAUSA_MAX_M = 200.0
# Atividade é intervalado com pelo menos 3 tiros.
MIN_TIROS_INTERVALADO = 3
# Volta "curta" (tiro de outra distância): de 150 a 700 m.
CURTA_MIN_M = 150.0
CURTA_MAX_M = 700.0

MODALIDADE_CORRIDA = "corrida"

# Ritmo habitual do atleta (@3): mediana do pace das corridas de mais de 3 km (sem esteira),
# anteriores à sessão, nas últimas 12 semanas; com menos de 10 na janela, todo o histórico.
HABITUAL_DISTANCIA_MIN_M = 3000.0
HABITUAL_JANELA_DIAS = 84
HABITUAL_MIN_CORRIDAS_JANELA = 10
# Os tiros da sessão precisam ter pace médio pelo menos 10% mais rápido que o ritmo habitual
# (@4; era 5% na @3).
HABITUAL_GANHO_MINIMO = 0.10

# @4, ritmo parecido: com 3 ou mais tiros, um tiro mais de 20% mais lento que a mediana dos
# tiros da sessão não é tiro (desaquecimento de 1 km que o relógio marcou como volta).
RITMO_PARECIDO_TOLERANCIA = 0.20
# @4, bloco contínuo: uma volta de ~1 km de corrida ao lado do tiro (olhando por cima das
# pausas) que seja menos de 15% mais lenta que ele indica progressivo ou fartlek, não tiro.
BLOCO_CONTINUO_GANHO_MINIMO = 0.15

# Intensidades do FIT que nunca são tiro (e valem como fronteira do treino).
INTENSIDADES_NUNCA_TIRO = frozenset({"rest", "recovery", "warmup", "cooldown"})
INTENSIDADES_FRONTEIRA = frozenset({"warmup", "cooldown"})
INTENSIDADES_CONHECIDAS = INTENSIDADES_NUNCA_TIRO | {"active", "interval"}


@dataclass(frozen=True)
class VoltaEntrada:
    ordem: int
    distancia_m: float
    duracao_s: float
    fc_media: float | None = None
    intensidade: str | None = None  # active/interval/rest/recovery/warmup/cooldown/...


@dataclass(frozen=True)
class ResultadoTiros:
    tiros: tuple[int, ...]  # ordens das voltas que são tiros
    recuperacoes: tuple[int, ...]  # voltas não-tiro entre o primeiro e o último tiro
    eh_intervalado: bool
    versao: str = VERSAO


def _pace_s_km(volta: VoltaEntrada) -> float | None:
    if volta.distancia_m <= 0 or volta.duracao_s <= 0:
        return None
    return volta.duracao_s / volta.distancia_m * 1000.0


def eh_candidata(volta: VoltaEntrada) -> bool:
    """Distância entre 950 e 1050 m, inclusive."""
    return abs(volta.distancia_m - DISTANCIA_ALVO_M) <= TOLERANCIA_M


def _intensidade(volta: VoltaEntrada) -> str | None:
    if volta.intensidade is None:
        return None
    valor = volta.intensidade.strip().lower()
    return valor if valor in INTENSIDADES_CONHECIDAS else None


def _pode_ser_tiro(volta: VoltaEntrada) -> bool:
    return (
        eh_candidata(volta)
        and _intensidade(volta) not in INTENSIDADES_NUNCA_TIRO
        and _pace_s_km(volta) is not None
    )


def _separa(tiro: VoltaEntrada, vizinha: VoltaEntrada | None) -> bool:
    """A volta vizinha separa o tiro do resto do treino?

    Separa: não existir vizinha (início ou fim da atividade); ser warmup/cooldown
    (fronteira do treino); ser uma pausa (< 200 m); ou ser uma recuperação, isto é,
    uma volta que não pode ser tiro (outra distância, rest/recovery) ou que é pelo menos
    8% mais lenta que o tiro. Uma vizinha de 1 km no mesmo ritmo (auto-lap de
    rodagem ou de bloco contínuo) não separa.
    """
    if vizinha is None or _intensidade(vizinha) in INTENSIDADES_FRONTEIRA:
        return True
    if vizinha.distancia_m < PAUSA_MAX_M:
        return True
    pace_vizinha = _pace_s_km(vizinha)
    if pace_vizinha is None:
        return True
    return _pace_s_km(tiro) <= pace_vizinha * (1.0 - GANHO_MINIMO_PACE)


def _vizinha_de_corrida(voltas: list[VoltaEntrada], i: int, passo: int) -> VoltaEntrada | None:
    """Primeira volta de corrida ao lado de ``voltas[i]``, pulando as pausas (< 200 m)."""
    j = i + passo
    while 0 <= j < len(voltas) and voltas[j].distancia_m < PAUSA_MAX_M:
        j += passo
    return voltas[j] if 0 <= j < len(voltas) else None


def _em_bloco_continuo(voltas: list[VoltaEntrada], i: int, ordens_tiros: set[int]) -> bool:
    """O tiro ``voltas[i]`` está colado, por cima de uma pausa, a um km de corrida quase tão rápido?

    Olha a primeira volta de corrida de cada lado (pulando pausas). Se for uma volta de ~1 km
    que não é tiro nem aquecimento/desaquecimento e o tiro for menos de 15% mais rápido que
    ela (``pace do tiro > pace da vizinha x 0,85``), o tiro é parte de um bloco contínuo.
    """
    tiro = voltas[i]
    for passo in (-1, 1):
        viz = _vizinha_de_corrida(voltas, i, passo)
        if viz is None or viz.ordem in ordens_tiros or not eh_candidata(viz):
            continue
        if _intensidade(viz) in INTENSIDADES_FRONTEIRA:
            continue
        pace_viz = _pace_s_km(viz)
        if pace_viz is not None and _pace_s_km(tiro) > pace_viz * (1.0 - BLOCO_CONTINUO_GANHO_MINIMO):
            return True
    return False


def _bloco_principal_e_1km(voltas: list[VoltaEntrada], tiros: list[VoltaEntrada]) -> bool:
    """O bloco principal do treino são os tiros de 1 km?

    Compara o volume (distância) dos tiros de 1 km com o das voltas curtas (150 a
    700 m) que não são tiro de 1 km e não estão rotuladas rest/recovery/warmup/
    cooldown: tiros curtos e também recuperações sem rótulo. Os tiros de 1 km valem
    se o volume deles for maior ou igual ao das voltas curtas. Cada recuperação sem
    rótulo pesa no máximo 70% de um tiro de 1 km, então num treino de 1 km elas somam
    bem menos que os tiros.
    """
    ordens = {t.ordem for t in tiros}
    curtas = sum(
        v.distancia_m
        for v in voltas
        if v.ordem not in ordens
        and CURTA_MIN_M <= v.distancia_m <= CURTA_MAX_M
        and _intensidade(v) not in INTENSIDADES_NUNCA_TIRO
    )
    return sum(t.distancia_m for t in tiros) >= curtas


def detectar_tiros(
    voltas: list[VoltaEntrada], modalidade: str = MODALIDADE_CORRIDA
) -> ResultadoTiros:
    """Classifica as voltas de uma atividade em tiros e recuperações.

    Tiro = volta de 950 a 1050 m, que não seja rest/recovery/warmup/cooldown, com as
    duas vizinhas separando-a (ver ``_separa``); com 3 ou mais, tira os de ritmo muito
    diferente e os colados a um bloco contínuo (@4). A intensidade só veta e marca
    fronteira: nunca basta para dizer que uma volta é tiro, o pace e a estrutura
    esforço-pausa decidem sempre.
    """
    if modalidade != MODALIDADE_CORRIDA or not voltas:
        return ResultadoTiros((), (), False)

    voltas = sorted(voltas, key=lambda v: v.ordem)
    tiros = []
    for i, volta in enumerate(voltas):
        if not _pode_ser_tiro(volta):
            continue
        anterior = voltas[i - 1] if i > 0 else None
        seguinte = voltas[i + 1] if i + 1 < len(voltas) else None
        if _separa(volta, anterior) and _separa(volta, seguinte):
            tiros.append(volta)

    if len(tiros) >= MIN_TIROS_INTERVALADO and not _bloco_principal_e_1km(voltas, tiros):
        tiros = []  # treino misto em que os tiros curtos pesam mais: não é de 1 km

    if len(tiros) >= MIN_TIROS_INTERVALADO:
        # Ritmo parecido (@4): tira o tiro bem mais lento que os outros (desaquecimento).
        mediana = median(_pace_s_km(t) for t in tiros)
        tiros = [t for t in tiros if _pace_s_km(t) <= mediana * (1.0 + RITMO_PARECIDO_TOLERANCIA)]
        # Bloco contínuo (@4): tiro colado a um km de corrida quase tão rápido.
        ordens = {t.ordem for t in tiros}
        posicao = {v.ordem: i for i, v in enumerate(voltas)}
        tiros = [t for t in tiros if not _em_bloco_continuo(voltas, posicao[t.ordem], ordens)]

    ordens_tiros = tuple(v.ordem for v in tiros)
    recuperacoes: tuple[int, ...] = ()
    if len(ordens_tiros) >= 2:
        primeiro, ultimo = ordens_tiros[0], ordens_tiros[-1]
        recuperacoes = tuple(
            v.ordem
            for v in voltas
            if primeiro < v.ordem < ultimo and v.ordem not in ordens_tiros
        )
    return ResultadoTiros(
        tiros=ordens_tiros,
        recuperacoes=recuperacoes,
        eh_intervalado=len(ordens_tiros) >= MIN_TIROS_INTERVALADO,
    )


# ---------------------------------------------------------------------------
# Agregação por sessão (issue #12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessaoTiros:
    """Uma atividade já classificada: os tiros (voltas) e se é intervalado."""

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


def sessao_de_voltas(
    atividade_id: int | str,
    data: date,
    voltas: list[VoltaEntrada],
    modalidade: str = MODALIDADE_CORRIDA,
) -> SessaoTiros:
    """Detecta os tiros (#11) e monta a sessão pronta para agregar."""
    resultado = detectar_tiros(voltas, modalidade)
    ordens = set(resultado.tiros)
    tiros = tuple(v for v in sorted(voltas, key=lambda v: v.ordem) if v.ordem in ordens)
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
