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
from datetime import date

VERSAO = "tiros_1km@2"

DISTANCIA_ALVO_M = 1000.0
# Tolerância de GPS/auto-lap: volta de 950 a 1050 m (inclusive) é candidata.
TOLERANCIA_M = 50.0
# Um tiro precisa ser pelo menos 8% mais rápido que a volta vizinha de recuperação.
GANHO_MINIMO_PACE = 0.08
# Volta vizinha mais curta que isto é pausa (parado/andando): sem comparação de pace.
PAUSA_MAX_M = 200.0
# Atividade é intervalado com pelo menos 3 tiros.
MIN_TIROS_INTERVALADO = 3

MODALIDADE_CORRIDA = "corrida"

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


def detectar_tiros(
    voltas: list[VoltaEntrada], modalidade: str = MODALIDADE_CORRIDA
) -> ResultadoTiros:
    """Classifica as voltas de uma atividade em tiros e recuperações.

    Tiro = volta de 950 a 1050 m, que não seja rest/recovery/warmup/cooldown, com as
    duas vizinhas separando-a (ver ``_separa``). A intensidade só veta e marca
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
    return PontoSessao(atividade_id, data, len(tiros), pace, fc, versao)


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
