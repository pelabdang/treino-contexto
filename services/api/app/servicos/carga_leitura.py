"""Leitura da carga (issue #142; ADR 0010, itens 5 a 7).

Nao calcula carga por atividade: le o que `app.servicos.carga` gravou em `carga_atividade`. A serie (CTL, ATL, TSB)
e calculada na leitura por `app.metricas.serie_carga.calcular_serie`, com o dia local da ADR 0003 feito aqui.
Nada de saude sai daqui: limiar, zonas, recordes e carga do Garmin ficam no banco.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, CargaAtividade
from app.metricas import carga as cg
from app.metricas import serie_carga as sc
from app.servicos.fuso import data_local


@dataclass(frozen=True)
class CargaLida:
    estado: str  # calculada | sem_carga
    carga: float | None
    metodo: str | None
    motivo: str | None
    cobertura_pct: float | None
    versao: str


@dataclass(frozen=True)
class SerieLida:
    serie: sc.SerieCarga
    pendentes: int  # elegiveis sem linha em carga_atividade (o comando ainda nao rodou para elas)
    atividades_importadas: int


def carga_da_atividade(session: Session, atividade_id: int) -> CargaLida | None:
    """None: sem linha (atividade ignorada, como `multiesporte_pai` e `troca`, ou carga ainda nao calculada)."""
    c = session.scalar(select(CargaAtividade).where(CargaAtividade.atividade_id == atividade_id))
    if c is None:
        return None
    return CargaLida(c.estado, c.carga, c.metodo, c.motivo, c.cobertura_pct, c.versao)


def serie_do_atleta(session: Session, atleta_id: int) -> SerieLida:
    q = (
        select(Atividade.inicio, Atividade.fuso_min, Atividade.subtipo, CargaAtividade.estado, CargaAtividade.carga,
               CargaAtividade.motivo)
        .outerjoin(CargaAtividade, CargaAtividade.atividade_id == Atividade.id)
        .where(Atividade.atleta_id == atleta_id)
    )
    entradas: list[sc.AtividadeCarga] = []
    ignoradas = pendentes = total = 0
    for inicio, fuso_min, subtipo, estado, carga, motivo in session.execute(q):
        total += 1
        if cg.ignorada(subtipo):
            ignoradas += 1
        elif estado is None:
            pendentes += 1
        else:
            dia = data_local(inicio, fuso_min)
            entradas.append(sc.AtividadeCarga(dia, carga) if estado == "calculada" else sc.AtividadeCarga(dia, motivo=motivo))
    return SerieLida(sc.calcular_serie(entradas, ignoradas), pendentes, total)
