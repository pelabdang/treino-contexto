"""Conferência da carga no banco (issue #144; ADR 0010, item 8): lê só, não grava.

Junta a nossa série diária (``serie_carga_do_atleta``, de ``carga_atividade``) com ``carga_garmin_dia`` (#174) e entrega à
função pura ``app.metricas.conferencia_carga.conferir``. Dado fisiológico (LGPD): só no banco local; nada vai para log.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CargaGarminDia
from app.metricas.conferencia_carga import Conferencia, DiaGarmin, conferir
from app.metricas.serie_carga import DiaCarga
from app.servicos.serie_carga_banco import serie_carga_do_atleta


@dataclass(frozen=True)
class ConferenciaDoBanco:
    nossa: list[DiaCarga]
    garmin: list[DiaGarmin]
    conferencia: Conferencia  # regra da ADR (descarta dias com atividade sem carga)
    complementar: Conferencia  # sem descartar: leitura complementar
    sem_linha: int  # atividades sem linha em carga_atividade


def conferencia_do_atleta(session: Session, atleta_id: int) -> ConferenciaDoBanco:
    lida = serie_carga_do_atleta(session, atleta_id)
    garmin = [
        DiaGarmin(g.dia, g.carga_aguda, g.carga_cronica, g.razao)
        for g in session.scalars(
            select(CargaGarminDia).where(CargaGarminDia.atleta_id == atleta_id).order_by(CargaGarminDia.dia)
        )
    ]
    dias = lida.serie.dias
    return ConferenciaDoBanco(
        dias, garmin, conferir(dias, garmin), conferir(dias, garmin, descartar_sem_carga=False), lida.sem_linha
    )
