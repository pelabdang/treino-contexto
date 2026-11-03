"""Posicao de inicio da atividade (ADR 0007, item 1): arredondada a 2 casas ja na leitura.

A coordenada exata nunca sai destas funcoes: so o par arredondado (ou `None`) e devolvido.
"""

from __future__ import annotations

import math

CASAS = 2  # ~1,1 km de latitude
SEMICIRCULO_INVALIDO = 0x7FFFFFFF  # valor "invalido" do FIT para sint32
SUBTIPOS_INDOOR = ("esteira", "piscina", "virtual")  # indoor nao guarda posicao (ADR 0007, item 2)


def graus_de_semicirculos(valor) -> float | None:
    """Semicirculos (inteiro de 32 bits do FIT) em graus; invalido ou nao numerico vira `None`."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if valor == SEMICIRCULO_INVALIDO:
        return None
    return valor * 180 / 2**31


def arredondar_posicao(lat, lon) -> tuple[float, float] | None:
    """O par arredondado a 2 casas, ou `None` se algum valor for ausente, nao numerico, fora da faixa ou se o
    par arredondado for (0, 0) (ponto "sem GPS")."""
    for v in (lat, lon):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    par = (round(float(lat), CASAS) + 0.0, round(float(lon), CASAS) + 0.0)  # + 0.0 troca -0.0 por 0.0
    return None if par == (0.0, 0.0) else par


def posicao_de_semicirculos(lat, lon) -> tuple[float, float] | None:
    return arredondar_posicao(graus_de_semicirculos(lat), graus_de_semicirculos(lon))


def e_indoor(subtipo: str | None) -> bool:
    return subtipo in SUBTIPOS_INDOOR
