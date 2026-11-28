"""Periodos do chat (ADR 0017, item 1): lista fechada resolvida pelo codigo a partir do "hoje" do atleta, ou um par `de` e `ate`.

Datas sao as locais do atleta (ADR 0003). Os dois lados sao incluidos. Nada aqui le o banco.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

PERIODOS = {  # nome -> (dias da janela, dias de deslocamento para tras, texto)
    "ultimos_7_dias": (7, 0, "últimos 7 dias"),
    "ultimos_28_dias": (28, 0, "últimos 28 dias"),
    "ultimos_28_dias_anteriores": (28, 28, "28 dias anteriores"),  # o par de comparacao de `ultimos_28_dias`
    "ultimas_12_semanas": (84, 0, "últimas 12 semanas"),
    "ultimos_6_meses": (183, 0, "últimos 6 meses"),
    "ultimo_ano": (365, 0, "último ano"),
}
JANELA_MAX_DIAS = 3 * 366


class PeriodoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Periodo:
    de: date
    ate: date
    texto: str

    def contem(self, dia: date) -> bool:
        return self.de <= dia <= self.ate


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise PeriodoInvalido("data") from None


def resolver(hoje: date, periodo: str | None = None, de: str | None = None, ate: str | None = None) -> Periodo | None:
    """`None` se nenhum dos tres veio (sem filtro). `PeriodoInvalido` se misturar `periodo` com `de`/`ate`, faltar um lado,
    a data for impossivel, `de` > `ate` ou a janela passar de 3 anos."""
    if periodo is None and de is None and ate is None:
        return None
    if periodo is not None:
        if de is not None or ate is not None or periodo not in PERIODOS:
            raise PeriodoInvalido("periodo")
        dias, atras, texto = PERIODOS[periodo]
        fim = hoje - timedelta(days=atras)
        return Periodo(fim - timedelta(days=dias - 1), fim, texto)
    if de is None or ate is None:
        raise PeriodoInvalido("de_ate")
    d, a = _data(de), _data(ate)
    if d > a or (a - d).days > JANELA_MAX_DIAS:
        raise PeriodoInvalido("de_ate")
    return Periodo(d, a, f"de {d.strftime('%d/%m/%Y')} a {a.strftime('%d/%m/%Y')}")
