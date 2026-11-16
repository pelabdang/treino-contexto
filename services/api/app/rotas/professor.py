"""Rotas do professor do piloto (Meta 11, ADR 0015). Por enquanto: o `PUT` em lote do tipo do treino (#425).

Toda rota daqui entra por `professor_da_rota` (404 uniforme) e le atleta so pelo filtro de `servicos/professor.py`.
O `422` nao repete o que foi enviado (so `loc`, `msg`, `type`) e o `500` e de texto fixo e neutro, "erro ao processar o pedido" (`RotaProfessor`, filha da `RotaCheckin`).
O log leva so `professor_id` e contagens.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.rotas.checkin import RotaCheckin as _RotaSemEco
from app.rotas.evolucao import Erro
from app.servicos import tipo_professor as tp
from app.servicos.professor import agora_utc, professor_da_rota

log = logging.getLogger(__name__)

TipoTreino = Literal["leve", "moderado", "longo", "intervalado", "fartlek"]

class RotaProfessor(_RotaSemEco):
    """422 sem eco da entrada e 500 de texto neutro (nada de "check-in" para o professor), so para as rotas do professor."""

    MSG_500 = "erro ao processar o pedido"
    LOG_500 = "professor"


router = APIRouter(prefix="/professores/{professor_id}", tags=["professor"], route_class=RotaProfessor)


class TipoItemIn(BaseModel):
    atividade_id: int
    tipo_treino: TipoTreino | None = None  # ausente: confirma o tipo que a atividade ja tem


class TiposConfirmadosOut(BaseModel):
    confirmados: int
    corrigidos: int


def _422(codigo: str, msg: str, loc: list[str | int]) -> HTTPException:
    return HTTPException(status_code=422, detail=[{"loc": loc, "msg": msg, "type": codigo}])


@router.put(
    "/tipos-de-treino",
    response_model=TiposConfirmadosOut,
    responses={
        404: {"model": Erro, "description": "Professor inexistente (`professor_inexistente`, uniforme) ou alguma atividade "
                                              "inexistente ou fora do vinculo e consentimento (`atividade_nao_encontrada`); lote nao salvo"},
        422: {"description": "Lote vazio, com mais de 200 itens, com `atividade_id` repetido ou tipo fora dos cinco (validacao); "
                             "ou `atividade_sem_tipo` (multiesporte ou sem tipo para confirmar). Lote nao salvo. Nunca repete o enviado"},
    },
)
def confirmar_tipos(
    itens: list[TipoItemIn] = Body(min_length=1, max_length=tp.LOTE_MAX),
    professor_id: int = Depends(professor_da_rota),
    session: Session = Depends(get_session),
    agora: datetime = Depends(agora_utc),
) -> TiposConfirmadosOut:
    """Confirma ou corrige, em lote e tudo ou nada, o tipo de treinos de alunos com vinculo e consentimento (ADR 0015, item 5)."""
    ids = [i.atividade_id for i in itens]
    if len(set(ids)) != len(ids):
        raise _422("atividade_repetida", "atividade repetida no lote", ["body"])
    try:
        r = tp.confirmar_ou_corrigir(session, professor_id, [tp.ItemLote(i.atividade_id, i.tipo_treino) for i in itens], agora)
    except tp.AtividadeNaoEncontrada:
        session.rollback()
        log.info("tipos-de-treino: lote recusado professor=%s itens=%s motivo=atividade_nao_encontrada", professor_id, len(itens))
        raise HTTPException(status_code=404, detail=[{"loc": ["body"], "msg": "atividade não encontrada", "type": "atividade_nao_encontrada"}])
    except tp.AtividadeSemTipo:
        session.rollback()
        log.info("tipos-de-treino: lote recusado professor=%s itens=%s motivo=atividade_sem_tipo", professor_id, len(itens))
        raise _422("atividade_sem_tipo", "atividade sem tipo para confirmar", ["body"])
    session.commit()
    log.info("tipos-de-treino: professor=%s confirmados=%s corrigidos=%s", professor_id, r.confirmados, r.corrigidos)
    return TiposConfirmadosOut(confirmados=r.confirmados, corrigidos=r.corrigidos)
