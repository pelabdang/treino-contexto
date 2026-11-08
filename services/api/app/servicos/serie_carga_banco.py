"""Série diária de carga (CTL, ATL, TSB) lida do banco (issue #143; ADR 0010, itens 5 e 6).

Junta ``atividade`` e ``carga_atividade`` (gravada pelo ``calcular_carga``, #141), converte cada ``inicio`` no dia LOCAL
(``data_local``, ADR 0003) e entrega à função pura ``app.metricas.serie_carga.calcular_serie``. Só leitura: não grava nada.
``multiesporte_pai`` e ``troca`` não entram (só a contagem). Atividade elegível sem linha de carga (``calcular_carga`` ainda
não rodou para ela) fica de fora e é contada em ``sem_linha``, para quem chama avisar.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade
from app.metricas import carga as cg
from app.metricas.serie_carga import AtividadeCarga, SerieCarga, calcular_serie
from app.servicos.fuso import data_local


@dataclass(frozen=True)
class SerieDoBanco:
    serie: SerieCarga
    sem_linha: int  # elegíveis sem linha em carga_atividade (rode worker.calcular_carga)


def serie_carga_do_atleta(session: Session, atleta_id: int) -> SerieDoBanco:
    atividades = session.scalars(
        select(Atividade).where(Atividade.atleta_id == atleta_id).options(selectinload(Atividade.carga))
    ).all()
    entrada: list[AtividadeCarga] = []
    ignoradas = sem_linha = 0
    for a in atividades:
        if cg.ignorada(a.subtipo):
            ignoradas += 1
            continue
        if a.carga is None:
            sem_linha += 1
            continue
        dia = data_local(a.inicio, a.fuso_min)
        if a.carga.estado == "calculada":
            entrada.append(AtividadeCarga(dia, carga=a.carga.carga))
        else:
            entrada.append(AtividadeCarga(dia, motivo=a.carga.motivo))
    return SerieDoBanco(calcular_serie(entrada, ignoradas_multiesporte=ignoradas), sem_linha)
