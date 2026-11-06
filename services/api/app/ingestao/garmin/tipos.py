"""Mapeia tipos Garmin (JSON e FIT) para modalidade e subtipo."""

from __future__ import annotations

# Multiesporte (issue #230, ADR 0009). Modalidade fica `outra`; o `subtipo` marca a atividade que agrupa as partes
# (`multiesporte_pai`) e a troca entre as partes (`troca`). Reconhecimento so por valores PUBLICOS:
# - FIT: enum `sport` do Profile do FIT SDK (Garmin, https://developer.garmin.com/fit/): `multisport` (valor 18) e
#   `transition` (valor 3, "multisport transition"). `fitdecode` entrega o nome do enum.
# - Exportacao Garmin (JSON): `activityType`/`sportType` com as chaves de tipo de atividade do Garmin Connect que
#   repetem esses nomes: `multi_sport`, `transition` e as modalidades-pai `triathlon`/`duathlon` (documentacao
#   publica do FIT SDK e das chaves de tipo usadas pelas bibliotecas abertas de Garmin Connect). O que uma
#   exportacao especifica traz nao e afirmado aqui: o passo `worker.reclassificar_subtipo` mostra o que casou.
SUBTIPO_PAI = "multiesporte_pai"
SUBTIPO_TROCA = "troca"
SUBTIPOS_MULTIESPORTE = frozenset({SUBTIPO_PAI, SUBTIPO_TROCA})
_VALORES_PAI = frozenset({"multi_sport", "multisport", "triathlon", "duathlon"})
_VALORES_TROCA = frozenset({"transition"})


def _multiesporte(t: str | None) -> str | None:
    """Subtipo multiesporte para um valor de esporte/tipo (igualdade exata, sem sufixo nem prefixo)."""
    v = (t or "").strip().lower()
    if v in _VALORES_PAI:
        return SUBTIPO_PAI
    if v in _VALORES_TROCA:
        return SUBTIPO_TROCA
    return None


def _por_texto(t: str) -> tuple[str, str | None]:
    t = t.lower()
    if "swim" in t:
        return "natacao", ("aguas_abertas" if "open_water" in t else "piscina" if "lap" in t else None)
    if "cycling" in t or "biking" in t or "bike" in t or t in ("virtual_ride", "e_bike_fitness"):
        return "ciclismo", ("esteira" if "indoor" in t else "virtual" if "virtual" in t else None)
    if "run" in t:
        sub = "esteira" if "treadmill" in t else "pista" if "track" in t else "trilha" if "trail" in t else None
        return "corrida", sub
    return "outra", None


def de_json(activity_type: str | None, sport_type: str | None) -> tuple[str, str | None]:
    """Usa activityType (mais especifico); cai para sportType."""
    for t in (activity_type, sport_type):
        sub = _multiesporte(t)
        if sub:
            return "outra", sub
    for t in (activity_type, sport_type):
        if t:
            modalidade, sub = _por_texto(t)
            if modalidade != "outra":
                return modalidade, sub
    return "outra", None


_SUB_FIT = {"treadmill": "esteira", "track": "pista", "trail": "trilha",
            "lap_swimming": "piscina", "open_water": "aguas_abertas", "indoor_cycling": "esteira",
            "virtual_activity": "virtual"}


def de_fit(sport: str | None, sub_sport: str | None) -> tuple[str, str | None]:
    multi = _multiesporte(sport)
    if multi:
        return "outra", multi
    modalidade, _ = _por_texto(sport or "")
    return modalidade, _SUB_FIT.get(sub_sport or "")
