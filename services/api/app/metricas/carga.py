"""Carga de treino por atividade: rTSS e hrTSS por volta (issue #138, ADR 0010 itens 4 e 7).

Função pura: sem banco, sem rede, sem IA. Quem resolve o limiar vigente na data (``limiar_vigente``) e grava o
resultado é o ``worker.calcular_carga`` (#141). A regra completa, os exemplos e as limitações estão em
docs/metricas/carga-treino.md. Qualquer mudança de fórmula, método preferido, ``COBERTURA_MIN``, lista de motivos,
tabela de modalidade/subtipo ou regra de limiar exige subir ``VERSAO``.

Fórmulas e fontes: forma do Training Stress Score, ``TSS = horas x IF^2 x 100`` (Coggan & Allen, *Training and Racing
with a Power Meter*, VeloPress; TrainingPeaks, "The Development of the Training Stress Score"). Uma hora no limiar
vale 100.
    rTSS_i  = duracao_i / 3600 x (v_i / velocidade_limiar)^2 x 100,   v_i = distancia_i / duracao_i   (m/s)
    hrTSS_i = duracao_i / 3600 x (fc_i / fc_limiar)^2 x 100
O rTSS segue a ideia do rTSS do TrainingPeaks, mas sem ajuste de subida (NGP). O hrTSS é adaptação própria, NÃO é o
hrTSS por zonas do TrainingPeaks. Carga da atividade = soma das voltas; volta sem o dado do método conta 0 e o método
só vale com cobertura >= ``COBERTURA_MIN`` da soma das durações.

``carga@2`` (issue #255): no hrTSS, se nenhuma volta tem FC mas a atividade tem ``fc_media``, a atividade entra como
volta única (``granularidade = 'atividade'`` quando o hrTSS é o método vencedor). Precisão menor que a por volta.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

VERSAO = "carga@2"

COBERTURA_MIN = 0.95
SUBTIPOS_IGNORADOS = frozenset({"multiesporte_pai", "troca"})
MODALIDADES_SEM_CARGA = frozenset({"natacao", "outra"})
MOTIVOS = (
    "sem_dados_saude",
    "sem_limiar_na_data",
    "sem_fc",
    "sem_pace",
    "cobertura_insuficiente",
    "modalidade_sem_carga",
)
_EPS = 1e-9


@dataclass(frozen=True)
class Volta:
    """Uma volta (ou a atividade inteira, quando não há voltas). ``duracao_s`` é o tempo em movimento."""

    duracao_s: float
    distancia_m: float | None
    fc_media: float | None


@dataclass(frozen=True)
class Limiares:
    """Limiares já resolvidos para o dia local da atividade (a vigência é da #141, não daqui).

    ``fc_bpm`` e ``velocidade_ms`` são ``None`` quando não há limiar daquela grandeza na data.
    ``atleta_tem_fc`` / ``atleta_tem_velocidade`` dizem se o atleta tem **alguma** linha daquela grandeza (em
    qualquer data): é o que separa ``sem_dados_saude`` (nenhuma) de ``sem_limiar_na_data`` (todas posteriores).
    """

    fc_bpm: float | None = None
    velocidade_ms: float | None = None
    atleta_tem_fc: bool = False
    atleta_tem_velocidade: bool = False


@dataclass(frozen=True)
class ResultadoCarga:
    """Espelha as colunas de ``carga_atividade`` (ADR 0010, item 5) que dependem só da conta."""

    estado: str  # calculada | sem_carga
    carga: float | None
    metodo: str | None  # rtss | hrtss
    carga_rtss: float | None
    carga_hrtss: float | None
    motivo: str | None
    cobertura_pct: float | None
    granularidade: str  # volta | atividade
    limiar_fc_bpm: float | None  # limiares efetivamente usados (auditoria)
    limiar_velocidade_ms: float | None


def ignorada(subtipo: str | None) -> bool:
    """``multiesporte_pai`` e ``troca`` ficam fora da conta: sem linha e sem motivo (ADR 0010, item 5)."""
    return subtipo in SUBTIPOS_IGNORADOS


def _tem_dado(metodo: str, v: Volta) -> bool:
    if not (v.duracao_s > 0):
        return False
    if metodo == "rtss":
        return v.distancia_m is not None and v.distancia_m > 0
    return v.fc_media is not None and v.fc_media > 0


def usa_fc_da_atividade(voltas: Sequence[Volta], atividade: Volta | None) -> bool:
    """``carga@2``: há voltas, nenhuma tem FC e a atividade tem ``fc_media`` (e duração): o hrTSS usa a atividade."""
    return bool(voltas) and atividade is not None and _tem_dado("hrtss", atividade) and not any(
        _tem_dado("hrtss", v) for v in voltas
    )


def _carga_do_metodo(metodo: str, voltas: Sequence[Volta], limiar: float) -> tuple[float, float, float]:
    """(carga, duração coberta, duração total). Volta sem dado conta 0."""
    total = sum(max(v.duracao_s, 0.0) for v in voltas)
    carga = coberto = 0.0
    for v in voltas:
        if not _tem_dado(metodo, v):
            continue
        intensidade = (v.distancia_m / v.duracao_s) / limiar if metodo == "rtss" else v.fc_media / limiar
        carga += v.duracao_s / 3600 * intensidade**2 * 100
        coberto += v.duracao_s
    return carga, coberto, total


def _sem_carga(motivo: str, granularidade: str, cobertura_pct: float | None = None) -> ResultadoCarga:
    return ResultadoCarga("sem_carga", None, None, None, None, motivo, cobertura_pct, granularidade, None, None)


def calcular_carga(
    modalidade: str,
    subtipo: str | None,
    voltas: Sequence[Volta],
    limiares: Limiares,
    atividade: Volta | None = None,
) -> ResultadoCarga | None:
    """Carga de uma atividade, ou ``None`` se ela é ignorada (``multiesporte_pai``/``troca``).

    ``voltas`` são os segmentos importados (todos os tipos). Sem voltas, usa-se ``atividade`` (totais) como volta
    única, com ``granularidade = 'atividade'``. Com voltas sem nenhuma FC, o hrTSS usa a FC média da atividade
    (``carga@2``; ``granularidade`` é a do método vencedor). Ordem do motivo (ADR 0010, item 7): modalidade sem carga; nenhum
    caminho com limiar na data (``sem_dados_saude`` ou ``sem_limiar_na_data``); senão o do primeiro caminho
    disponível (``sem_fc``, ``sem_pace`` ou ``cobertura_insuficiente``). Nunca devolve carga aproximada.
    """
    for nome, valor in (("fc_bpm", limiares.fc_bpm), ("velocidade_ms", limiares.velocidade_ms)):
        if valor is not None and not (math.isfinite(valor) and valor > 0):
            raise ValueError(f"limiar {nome} deve ser positivo: {valor!r}")
    if ignorada(subtipo):
        return None
    if voltas:
        granularidade, entrada = "volta", list(voltas)
    else:
        granularidade, entrada = "atividade", ([atividade] if atividade is not None else [])
    if modalidade in MODALIDADES_SEM_CARGA:
        return _sem_carga("modalidade_sem_carga", granularidade)

    usa_pace = modalidade == "corrida" and subtipo != "esteira"
    caminhos: list[tuple[str, float | None, bool]] = []  # (método, limiar na data, atleta tem a grandeza)
    if usa_pace:
        caminhos.append(("rtss", limiares.velocidade_ms, limiares.atleta_tem_velocidade))
    caminhos.append(("hrtss", limiares.fc_bpm, limiares.atleta_tem_fc))
    disponiveis = [(m, lim) for m, lim, _ in caminhos if lim is not None]
    if not disponiveis:
        if any(tem for _, _, tem in caminhos):
            return _sem_carga("sem_limiar_na_data", granularidade)
        return _sem_carga("sem_dados_saude", granularidade)

    validos: dict[str, tuple[float, float]] = {}  # método -> (carga, cobertura em %)
    primeiro: tuple[str, float, float] | None = None  # método, cobertura, coberto (do primeiro disponível)
    fc_da_atividade = usa_fc_da_atividade(voltas, atividade)
    for metodo, lim in disponiveis:
        base = [atividade] if metodo == "hrtss" and fc_da_atividade else entrada
        carga, coberto, total = _carga_do_metodo(metodo, base, lim)
        cobertura = coberto / total if total > 0 else 0.0
        if primeiro is None:
            primeiro = (metodo, cobertura, coberto)
        if coberto > 0 and cobertura >= COBERTURA_MIN - _EPS:
            validos[metodo] = (carga, cobertura * 100)

    if not validos:
        metodo, cobertura, coberto = primeiro
        if coberto <= 0:
            return _sem_carga("sem_pace" if metodo == "rtss" else "sem_fc", granularidade)
        return _sem_carga("cobertura_insuficiente", granularidade, cobertura * 100)

    vencedor = next(m for m, _ in disponiveis if m in validos)
    if vencedor == "hrtss" and fc_da_atividade:
        granularidade = "atividade"
    carga_rtss = validos["rtss"][0] if "rtss" in validos else None
    carga_hrtss = validos["hrtss"][0] if "hrtss" in validos else None
    return ResultadoCarga(
        "calculada",
        validos[vencedor][0],
        vencedor,
        carga_rtss,
        carga_hrtss,
        None,
        validos[vencedor][1],
        granularidade,
        limiares.fc_bpm if carga_hrtss is not None else None,
        limiares.velocidade_ms if carga_rtss is not None else None,
    )
