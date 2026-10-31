"""Conversao de unidades da exportacao Garmin, num lugar so.

O JSON resumido usa milissegundos e centimetros. O FIT, lido com fitdecode,
ja chega em segundos e metros (fitdecode aplica a escala do perfil FIT).
"""

from __future__ import annotations

from datetime import datetime, timezone


def ms_para_s(ms: float) -> float:
    return ms / 1000


def cm_para_m(cm: float) -> float:
    return cm / 100


def epoch_ms_para_datetime(ms: float) -> datetime:
    """Milissegundos desde 1970 (UTC) para datetime com fuso UTC."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def para_utc(dt: datetime) -> datetime:
    """Garante fuso: datetime sem fuso e tratado como UTC (padrao do FIT)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hora_de_parede(local_ms: float) -> datetime:
    """`startTimeLocal` da Garmin: hora de parede local contada como se fosse UTC. Devolve datetime naive."""
    return epoch_ms_para_datetime(local_ms).replace(tzinfo=None)
