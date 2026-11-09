"""Semana-padrao do atleta: GET e PUT (issue #264, ADR 0011, item 9)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from app.db.models import Atleta, SemanaPadrao
from app.db.session import get_session
from app.rotas.evolucao import Erro
from app.servicos import semana_padrao as sp
from app.servicos.fuso import FUSO_PADRAO
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}", tags=["semana-padrão"])

Modalidade = Literal["corrida", "natacao", "ciclismo"]
TipoTreino = Literal["leve", "moderado", "longo", "intervalado", "fartlek"]
DefinidoPor = Literal["atleta", "professor"]
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

_404 = {404: {"model": Erro, "description": "Atleta não encontrado"}}


class ItemIn(BaseModel):
    dia_semana: int  # ISO: 1 = segunda ... 7 = domingo
    modalidade: Modalidade
    tipo_treino: TipoTreino | None = None  # null: treina essa modalidade nesse dia, sem tipo

    @model_validator(mode="after")
    def _dia(self) -> "ItemIn":
        if not 1 <= self.dia_semana <= 7:
            raise ValueError("dia_semana deve ir de 1 (segunda) a 7 (domingo)")
        return self


class SemanaPadraoIn(BaseModel):
    vigente_desde: date
    definido_por: DefinidoPor  # declarado, nao verificado: ainda nao ha login (ADR 0011, item 10)
    itens: list[ItemIn]  # [] e valido: encerra o plano a partir de `vigente_desde`

    @model_validator(mode="after")
    def _sem_repetidos(self) -> "SemanaPadraoIn":
        vistos = [(i.dia_semana, i.modalidade) for i in self.itens]
        if len(set(vistos)) != len(vistos):
            raise ValueError("um item por modalidade por dia: (dia_semana, modalidade) repetido")
        return self


class ItemOut(BaseModel):
    dia_semana: int
    dia_semana_texto: str
    modalidade: Modalidade
    tipo_treino: TipoTreino | None


class VigenteOut(BaseModel):
    vigente_desde: date
    definido_por: DefinidoPor
    definido_em: datetime  # America/Sao_Paulo
    itens: list[ItemOut]  # em ordem de dia e modalidade


class VigenciaOut(BaseModel):
    vigente_desde: date
    definido_por: DefinidoPor
    total_itens: int


class SemanaPadraoOut(BaseModel):
    atleta_id: int
    em: date
    vigente: VigenteOut | None  # null: nenhuma vigencia com vigente_desde <= em. Vigencia vazia vem com itens = []
    vigencias: list[VigenciaOut]  # da mais nova para a mais antiga


class SemanaPadraoGravadaOut(VigenteOut):
    atividades_reaplicadas: int  # quantas atividades mudaram de tipo, origem ou divergencia (sempre 0 ate a #265)


def _definido_em(dt: datetime) -> datetime:
    if dt.tzinfo is None:  # SQLite devolve sem fuso; o banco grava UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_PADRAO)


def _vigente_out(s: SemanaPadrao) -> dict:
    itens = sorted(s.itens, key=lambda i: (i.dia_semana, i.modalidade))
    return dict(
        vigente_desde=s.vigente_desde, definido_por=s.definido_por, definido_em=_definido_em(s.definido_em),
        itens=[ItemOut(dia_semana=i.dia_semana, dia_semana_texto=DIAS[i.dia_semana - 1], modalidade=i.modalidade,
                       tipo_treino=i.tipo_treino) for i in itens],
    )


def _atleta_existe(session: Session, atleta_id: int) -> None:
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")


@router.get("/semana-padrao", response_model=SemanaPadraoOut, operation_id="semanaPadraoDoAtleta", responses=_404)
def semana_padrao_do_atleta(atleta_id: int, em: date | None = None, session: Session = Depends(get_session)) -> SemanaPadraoOut:
    """A semana vigente em `em` (AAAA-MM-DD; padrão: hoje em America/Sao_Paulo) e o histórico de vigências."""
    _atleta_existe(session, atleta_id)
    em = em or sp.hoje_local()
    s = sp.vigente_em(session, atleta_id, em)
    return SemanaPadraoOut(
        atleta_id=atleta_id, em=em, vigente=VigenteOut(**_vigente_out(s)) if s else None,
        vigencias=[VigenciaOut(vigente_desde=v.vigente_desde, definido_por=v.definido_por, total_itens=v.total_itens)
                   for v in sp.vigencias(session, atleta_id)],
    )


@router.put("/semana-padrao", response_model=SemanaPadraoGravadaOut, operation_id="gravarSemanaPadrao", responses=_404)
def gravar_semana_padrao(atleta_id: int, corpo: SemanaPadraoIn, session: Session = Depends(get_session)) -> SemanaPadraoGravadaOut:
    """Cria ou substitui a vigência `vigente_desde` (reenviar é idempotente). `itens: []` encerra o plano. Não há `DELETE`.
    A reaplicação do tipo nas atividades é da #265: por enquanto `atividades_reaplicadas` é sempre 0."""
    _atleta_existe(session, atleta_id)
    linha, reaplicadas = sp.gravar_vigencia(
        session, atleta_id, corpo.vigente_desde, corpo.definido_por,
        [sp.ItemNovo(i.dia_semana, i.modalidade, i.tipo_treino) for i in corpo.itens],
    )
    return SemanaPadraoGravadaOut(**_vigente_out(linha), atividades_reaplicadas=reaplicadas)
