"""Leitura de um arquivo FIT com fitdecode (so o que a Meta 1 precisa)."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime

import fitdecode

from .modelos import VoltaImportada
from .unidades import para_utc


@dataclass
class FitLido:
    inicio: datetime
    sport: str | None
    sub_sport: str | None
    duracao_s: float | None
    distancia_m: float | None
    fc_media: int | None
    id_derivado: str
    voltas: list[VoltaImportada] = field(default_factory=list)


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def _int(v) -> int | None:
    return int(v) if isinstance(v, (int, float)) else None


def _txt(v) -> str | None:
    return str(v) if v is not None else None


class FitSemAtividade(ValueError):
    """FIT valido, mas que nao e uma atividade (monitoramento diario, sono, configuracao...)."""


def ler_fit(conteudo: bytes) -> FitLido:
    """Le um FIT. Levanta ValueError se estiver corrompido ou sem dados de atividade."""
    file_id: dict = {}
    session: dict = {}
    laps: list[dict] = []
    try:
        with fitdecode.FitReader(io.BytesIO(conteudo)) as leitor:
            for quadro in leitor:
                if not isinstance(quadro, fitdecode.FitDataMessage):
                    continue
                dados = {c.name: c.value for c in quadro.fields}
                if quadro.name == "file_id":
                    file_id = dados
                    tipo = dados.get("type")
                    if tipo is not None and str(tipo) != "activity":
                        # file_id e a 1a mensagem: nao decodifica o resto de um arquivo que nao e atividade
                        raise FitSemAtividade(f"FIT do tipo {tipo}, nao e atividade")
                elif quadro.name == "session" and not session:
                    session = dados
                elif quadro.name == "lap":
                    laps.append(dados)
    except FitSemAtividade:
        raise
    except Exception as e:  # fitdecode levanta varios tipos (CRC, truncado...)
        raise ValueError(f"FIT invalido: {e}") from e

    inicio = session.get("start_time") or (laps[0].get("start_time") if laps else None)
    if not isinstance(inicio, datetime):
        raise ValueError("FIT sem horario de inicio (sem session nem lap)")
    inicio = para_utc(inicio)

    voltas = []
    for i, lap in enumerate(laps):
        t = lap.get("start_time")
        offset = (para_utc(t) - inicio).total_seconds() if isinstance(t, datetime) else 0.0
        voltas.append(
            VoltaImportada(
                ordem=i,
                inicio_offset_s=offset,
                duracao_s=_num(lap.get("total_timer_time")) or 0.0,
                distancia_m=_num(lap.get("total_distance")) or 0.0,
                fc_media=_int(lap.get("avg_heart_rate")),
                intensidade=_txt(lap.get("intensity")),
            )
        )

    serial, criado = file_id.get("serial_number"), file_id.get("time_created")
    if serial is not None and isinstance(criado, datetime):
        id_derivado = f"fit-{serial}-{int(para_utc(criado).timestamp())}"
    else:  # sem file_id utilizavel: hash do conteudo (estavel entre importacoes)
        id_derivado = "fit-" + hashlib.sha1(conteudo).hexdigest()[:16]

    dur = _num(session.get("total_timer_time"))
    dist = _num(session.get("total_distance"))
    if dur is None and voltas:
        dur = sum(v.duracao_s for v in voltas)
    if dist is None and voltas:
        dist = sum(v.distancia_m for v in voltas)
    return FitLido(
        inicio=inicio,
        sport=_txt(session.get("sport")),
        sub_sport=_txt(session.get("sub_sport")),
        duracao_s=dur,
        distancia_m=dist,
        fc_media=_int(session.get("avg_heart_rate")),
        id_derivado=id_derivado,
        voltas=voltas,
    )
