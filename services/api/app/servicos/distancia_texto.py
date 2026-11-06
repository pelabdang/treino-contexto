"""Texto da distância da atividade (#216, ADR 0004 adendo 3). Fica aqui para a atividade e o treino de transição (#170) usarem a mesma regra."""

from __future__ import annotations


def distancia_da_atividade(modalidade: str, m: float | None) -> str | None:
    """Texto da distancia da atividade (#216): natacao em metros com ponto de milhar, o resto em km com 2 casas."""
    if m is None or m <= 0:
        return None
    if modalidade == "natacao":
        return f"{int(m + 0.5):,}".replace(",", ".") + " m"
    return f"{m / 1000:.2f}".replace(".", ",") + " km"
