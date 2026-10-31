"""Tiros de 1 km: detecção (issue #11) e agregação por sessão (issue #12).

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
from datetime import date
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
