"""Detecção dos tiros de 1 km numa corrida (issue #11).

Funções puras: sem banco, sem IA. A regra completa e os limites estão em
docs/metricas/tiros-1km.md. Qualquer mudança de regra ou de constante exige
subir ``VERSAO`` (a versão é gravada junto do resultado).

Fonte: regra própria do projeto (não há artigo). O uso da mediana como
referência de pace é a estatística robusta padrão para separar esforços de um
ritmo-base: ela não é puxada pelos poucos tiros rápidos quando eles são
minoria das voltas.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

VERSAO = "tiros_1km@1"

DISTANCIA_ALVO_M = 1000.0
# Tolerância de GPS/auto-lap: volta de 950 a 1050 m (inclusive) é candidata.
TOLERANCIA_M = 50.0
# Sem intensidade: tiro precisa ser pelo menos 8% mais rápido que a mediana
# do pace das voltas da atividade (ver nota da métrica para a justificativa).
GANHO_MINIMO_PACE = 0.08
# Atividade é intervalado com pelo menos 3 tiros.
MIN_TIROS_INTERVALADO = 3

MODALIDADE_CORRIDA = "corrida"

INTENSIDADES_TIRO = frozenset({"active", "interval"})
INTENSIDADES_NUNCA_TIRO = frozenset({"rest", "recovery", "warmup", "cooldown"})
INTENSIDADES_CONHECIDAS = INTENSIDADES_TIRO | INTENSIDADES_NUNCA_TIRO


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


def _intensidade_informativa(voltas: list[VoltaEntrada]) -> bool:
    """Intensidade só ajuda se houver contraste entre voltas.

    O auto-lap de 1 km de uma rodagem leve costuma vir todo como ``active``;
    nesse caso a intensidade não distingue nada e usamos a regra por pace.
    """
    valores = {_intensidade(v) for v in voltas}
    valores.discard(None)
    return len(valores) >= 2


def detectar_tiros(
    voltas: list[VoltaEntrada], modalidade: str = MODALIDADE_CORRIDA
) -> ResultadoTiros:
    """Classifica as voltas de uma atividade em tiros e recuperações."""
    if modalidade != MODALIDADE_CORRIDA or not voltas:
        return ResultadoTiros((), (), False)

    voltas = sorted(voltas, key=lambda v: v.ordem)
    candidatas = [v for v in voltas if eh_candidata(v)]

    if _intensidade_informativa(voltas):
        tiros = [v for v in candidatas if _intensidade(v) in INTENSIDADES_TIRO]
    else:
        paces = [p for p in (_pace_s_km(v) for v in voltas) if p is not None]
        if not paces:
            return ResultadoTiros((), (), False)
        limite = median(paces) * (1.0 - GANHO_MINIMO_PACE)
        tiros = []
        for v in candidatas:
            pace = _pace_s_km(v)
            if pace is not None and pace <= limite:
                tiros.append(v)

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
