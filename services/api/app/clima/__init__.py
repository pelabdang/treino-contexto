"""Clima da atividade (Meta 4, ADR 0007). Weather data by Open-Meteo.com (CC BY 4.0)."""

from .cliente import (
    USER_AGENT,
    ClienteClima,
    ClienteOpenMeteo,
    ClimaMedio,
    ResultadoClima,
)

__all__ = ["ClienteClima", "ClienteOpenMeteo", "ClimaMedio", "ResultadoClima", "USER_AGENT"]
