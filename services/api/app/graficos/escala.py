"""Escala mínima dos eixos de pace e FC (issue #63; ADR 0004, decisão 2).

Regra única do PNG (``render_png``) e do bloco ``eixos`` do JSON (#66). Função
pura, sem matplotlib. Regra própria do projeto; não há artigo.

Problema (QA da Meta 1, #18): o eixo se ajustava aos dados, então 1 a 2 bpm
de diferença parecia uma subida grande. Se a faixa dos dados é menor que a
amplitude mínima, os dados ficam centralizados numa faixa dessa amplitude.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.metricas.tiros_1km import formatar_pace

AMPLITUDE_MIN_FC_BPM = 5.0  # decisão do Angelo; não muda sem ele
AMPLITUDE_MIN_PACE_S_KM = 30.0  # valor inicial (Caio e Bia podem ajustar, na nota)
PASSO_FC_BPM = 1.0  # 1 bpm dá 5 ou 6 marcas numa faixa de 5 bpm (passo 2 podia dar só 2)
PASSO_PACE_S_KM = 10.0  # faixa de 30 s/km tem 3 ou 4 marcas (com 15 tinha só 2; issue #87)
MAX_MARCAS = 8  # acima disso o passo sobe pelos fatores de _FATORES_PASSO
_FATORES_PASSO = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)
_EPS = 1e-9


@dataclass(frozen=True)
class Marca:
    valor: float
    rotulo: str


@dataclass(frozen=True)
class Escala:
    min: float
    max: float
    marcas: tuple[Marca, ...]


def _rotulo_inteiro(v: float) -> str:
    return f"{v:g}"


def _multiplos(minimo: float, maximo: float, passo: float) -> list[float]:
    k0 = math.ceil(minimo / passo - _EPS)
    k1 = math.floor(maximo / passo + _EPS)
    return [k * passo for k in range(k0, k1 + 1)]


def escala_eixo(
    valores: Sequence[float | None],
    amplitude_minima: float,
    passo: float,
    rotulo: Callable[[float], str] = _rotulo_inteiro,
    max_marcas: int = MAX_MARCAS,
) -> Escala | None:
    """Faixa e marcas de um eixo. ``None`` se não há nenhum valor.

    - Faixa dos dados >= ``amplitude_minima``: ``min`` e ``max`` são os dados.
    - Faixa menor: centro = (menor + maior) / 2 e faixa = centro +- amplitude/2.
    - Marcas nos múltiplos de ``passo`` dentro da faixa. Se passarem de
      ``max_marcas``, o passo sobe (x2, x5, x10...) até caber; continua múltiplo
      de ``passo``.
    - ``rotulo`` formata cada marca (pace: ``formatar_pace``).
    """
    dados = [v for v in valores if v is not None]
    if not dados:
        return None
    menor, maior = min(dados), max(dados)
    if maior - menor < amplitude_minima:
        centro = (menor + maior) / 2
        menor, maior = centro - amplitude_minima / 2, centro + amplitude_minima / 2
    for fator in _FATORES_PASSO:
        valores_marcas = _multiplos(menor, maior, passo * fator)
        if len(valores_marcas) <= max_marcas:
            break
    return Escala(menor, maior, tuple(Marca(v, rotulo(v)) for v in valores_marcas))


def escala_pace(valores: Sequence[float | None]) -> Escala | None:
    """Eixo de pace (s/km): mínimo 30 s/km, marcas de 10 em 10, rótulo ``formatar_pace``."""
    return escala_eixo(valores, AMPLITUDE_MIN_PACE_S_KM, PASSO_PACE_S_KM, formatar_pace)


def escala_fc(valores: Sequence[float | None]) -> Escala | None:
    """Eixo de FC (bpm): mínimo 5 bpm, marcas de 1 bpm (sobe se a faixa for larga)."""
    return escala_eixo(valores, AMPLITUDE_MIN_FC_BPM, PASSO_FC_BPM)
