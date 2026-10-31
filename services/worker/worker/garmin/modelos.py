"""Objetos simples devolvidos pelo parser (sem banco)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

MODALIDADES = ("corrida", "natacao", "ciclismo", "outra")


@dataclass(frozen=True)
class VoltaImportada:
    ordem: int  # 0, 1, 2... na ordem do arquivo
    inicio_offset_s: float  # segundos desde o inicio da sessao no FIT
    duracao_s: float  # total_timer_time (tempo em movimento)
    distancia_m: float
    fc_media: int | None
    intensidade: str | None  # active, rest, warmup, cooldown, recovery, interval, other; None se ausente


@dataclass
class AtividadeImportada:
    fonte_id: str
    modalidade: str  # um de MODALIDADES
    inicio: datetime  # com fuso, UTC
    duracao_s: float | None
    distancia_m: float | None
    fc_media: int | None
    arquivo_bruto: str | None  # caminho do original dentro da exportacao
    fonte: str = "garmin_export"
    subtipo: str | None = None  # esteira, pista, trilha, piscina, aguas_abertas
    voltas: list[VoltaImportada] = field(default_factory=list)
