"""Data local da sessão (ADR 0003)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FUSO_PADRAO = ZoneInfo("America/Sao_Paulo")


def data_local(inicio: datetime, fuso_min: int | None) -> date:
    """Data do início da atividade no horário local do atleta.

    Com `fuso_min` (deslocamento em minutos da exportação), data de `inicio + fuso_min`.
    Sem ele, `America/Sao_Paulo` aplicado ao instante UTC. `inicio` sem fuso (SQLite) é UTC.
    """
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    if fuso_min is not None:
        return (inicio.astimezone(timezone.utc) + timedelta(minutes=fuso_min)).date()
    return inicio.astimezone(FUSO_PADRAO).date()
