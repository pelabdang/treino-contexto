"""Zonas de FC vigentes numa atividade, lidas da mensagem `time_in_zone` da sessao do FIT (Meta 6, #136).

O JSON `heartRateZones` e so o retrato de hoje; o historico de zonas existe apenas nos FIT, por sessao
(`docs/modulos/ingestao-garmin.md`, "Zonas de FC"). Pura: sem banco, sem rede.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime, timedelta

import fitdecode

from . import tipos
from .modelos_saude import ORIGEM_FIT, ZonaFc
from .unidades import para_utc

log = logging.getLogger(__name__)


def _int(v) -> int | None:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _txt(v) -> str | None:
    return str(v) if v is not None else None


def esporte_da_zona(modalidade: str) -> str:
    """Perfil de esporte das zonas: `corrida`, `ciclismo` ou `padrao` (o perfil DEFAULT da Garmin)."""
    return modalidade if modalidade in ("corrida", "ciclismo") else "padrao"


def ler_zonas_fit(conteudo: bytes) -> tuple[datetime, ZonaFc] | None:
    """Zonas da sessao de um FIT: `(inicio UTC da sessao, zonas)`, ou `None` se o FIT nao as traz.

    Usa so a `time_in_zone` com `reference_mesg = session` (as de lap, split e set sao outras). Os 6 itens de
    `hr_zone_high_boundary` sao os limites superiores: o 1o e o piso da zona 1, o 2o o da zona 2... o 5o o da
    zona 5 e o 6o o teto da zona 5. FIT invalido, sem sessao ou sem os 6 limites: `None` (sem excecao).
    `vigente_desde` e o dia local da sessao (hora de parede do atleta, pela diferenca entre `local_timestamp`
    e `timestamp` da mensagem `activity`; sem ela, o dia em UTC).
    """
    tiz: dict | None = None
    sessao: dict | None = None
    atividade: dict = {}
    try:
        with fitdecode.FitReader(io.BytesIO(conteudo)) as leitor:
            for q in leitor:
                if not isinstance(q, fitdecode.FitDataMessage):
                    continue
                if q.name == "file_id":
                    tipo = q.get_value("type", fallback=None)
                    if tipo is not None and str(tipo) != "activity":
                        return None
                elif q.name == "time_in_zone" and tiz is None:
                    if str(q.get_value("reference_mesg", fallback=None)) == "session":
                        tiz = {c.name: c.value for c in q.fields}
                elif q.name == "session" and sessao is None:
                    sessao = {c.name: c.value for c in q.fields}
                elif q.name == "activity":
                    atividade = {c.name: c.value for c in q.fields}
    except Exception as e:  # fitdecode levanta varios tipos (CRC, truncado...)
        log.warning("FIT ilegivel ao procurar zonas: %s", type(e).__name__)
        return None
    if tiz is None or sessao is None or not isinstance(sessao.get("start_time"), datetime):
        return None
    limites = tiz.get("hr_zone_high_boundary")
    if not isinstance(limites, (list, tuple)) or len(limites) < 6:
        return None
    b = [_int(x) for x in limites[:6]]
    if any(x is None or x <= 0 for x in b) or b != sorted(b):
        return None

    inicio = para_utc(sessao["start_time"])
    modalidade, _ = tipos.de_fit(_txt(sessao.get("sport")), _txt(sessao.get("sub_sport")))
    return inicio, ZonaFc(
        esporte=esporte_da_zona(modalidade), origem=ORIGEM_FIT, vigente_desde=_dia_local(inicio, atividade),
        metodo=_txt(tiz.get("hr_calc_type")), fc_max_bpm=_int(tiz.get("max_heart_rate")),
        fc_repouso_bpm=_int(tiz.get("resting_heart_rate")),
        zona1_min_bpm=b[0], zona2_min_bpm=b[1], zona3_min_bpm=b[2], zona4_min_bpm=b[3], zona5_min_bpm=b[4],
        zona5_max_bpm=b[5],
    )


def _dia_local(inicio_utc: datetime, atividade: dict) -> date:
    ts, local = atividade.get("timestamp"), atividade.get("local_timestamp")
    if isinstance(ts, datetime) and isinstance(local, datetime):
        desloc = para_utc(local) - para_utc(ts)
        if abs(desloc) <= timedelta(hours=14):
            return (inicio_utc + desloc).date()
    return inicio_utc.date()
