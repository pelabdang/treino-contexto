"""Mapeia tipos Garmin (JSON e FIT) para modalidade e subtipo."""

from __future__ import annotations


def _por_texto(t: str) -> tuple[str, str | None]:
    t = t.lower()
    if "swim" in t:
        return "natacao", ("aguas_abertas" if "open_water" in t else "piscina" if "lap" in t else None)
    if "cycling" in t or "biking" in t or "bike" in t or t in ("virtual_ride", "e_bike_fitness"):
        return "ciclismo", ("esteira" if "indoor" in t else None)
    if "run" in t:
        sub = "esteira" if "treadmill" in t else "pista" if "track" in t else "trilha" if "trail" in t else None
        return "corrida", sub
    return "outra", None


def de_json(activity_type: str | None, sport_type: str | None) -> tuple[str, str | None]:
    """Usa activityType (mais especifico); cai para sportType."""
    for t in (activity_type, sport_type):
        if t:
            modalidade, sub = _por_texto(t)
            if modalidade != "outra":
                return modalidade, sub
    return "outra", None


_SUB_FIT = {"treadmill": "esteira", "track": "pista", "trail": "trilha",
            "lap_swimming": "piscina", "open_water": "aguas_abertas", "indoor_cycling": "esteira"}


def de_fit(sport: str | None, sub_sport: str | None) -> tuple[str, str | None]:
    modalidade, _ = _por_texto(sport or "")
    return modalidade, _SUB_FIT.get(sub_sport or "")
