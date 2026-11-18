"""Consentimento do atleta e o termo (issue #501, ADR 0016, item 7).

`GET/PUT/DELETE` sob `/atletas/{atleta_id}/professores...` so para o atleta dono (a dependencia `atleta_da_sessao` entra no
`include_router`); `GET /termo-de-consentimento` para qualquer conta com sessao. O professor nao usa estas rotas.
O 422 nao repete o enviado e o 500 e neutro. O log leva so ids.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.autenticacao import MSG_401, ContaAtual, conta_liberada
from app.db.session import get_session
from app.rotas.checkin import RotaCheckin as _RotaSemEco
from app.rotas.evolucao import Erro
from app.servicos import consentimento as svc
from app.servicos.professor import agora_utc

log = logging.getLogger(__name__)


class RotaConsentimento(_RotaSemEco):
    MSG_500 = "erro ao processar o pedido"
    LOG_500 = "consentimento"


router = APIRouter(prefix="/atletas/{atleta_id}/professores", tags=["consentimento"], route_class=RotaConsentimento)
router_termo = APIRouter(tags=["consentimento"], route_class=RotaConsentimento)


class TermoOut(BaseModel):
    versao: str
    provisorio: bool  # o app mostra a faixa "Texto provisório, ainda sem revisão jurídica"
    texto: str


class VinculoOut(BaseModel):
    professor_id: int
    nome: str
    consentimento: bool  # ativo agora: aceito, nao retirado e na versao vigente do termo
    termo_versao: str | None
    consentimento_em: datetime | None
    consentimento_revogado_em: datetime | None
    termo_desatualizado: bool  # aceitou uma versao antiga: o professor nao ve ate aceitar de novo


class ProfessoresOut(BaseModel):
    atleta_id: int
    termo_vigente: str
    professores: list[VinculoOut]


class AceiteIn(BaseModel):
    termo_versao: str = Field(min_length=1, max_length=40)


_404 = {"model": Erro, "description": "Sem acesso ou sem vínculo com esse professor (o mesmo 404 de atleta inexistente)"}


@router.get("", response_model=ProfessoresOut, operation_id="professoresDoAtleta", responses={404: _404, 401: {"model": Erro, "description": MSG_401}})
def professores_do_atleta(atleta_id: int, session: Session = Depends(get_session), agora: datetime = Depends(agora_utc)) -> ProfessoresOut:
    vs = svc.vinculos_do_atleta(session, atleta_id, agora)
    return ProfessoresOut(atleta_id=atleta_id, termo_vigente=svc.TERMO_VIGENTE, professores=[VinculoOut(**v.__dict__) for v in vs])


@router.put(
    "/{professor_id}/consentimento",
    response_model=VinculoOut,
    operation_id="aceitarConsentimento",
    responses={404: _404, 409: {"model": Erro, "description": "`termo_versao` diferente da vigente: leia o termo de novo"}},
)
def aceitar(atleta_id: int, professor_id: int, corpo: AceiteIn, session: Session = Depends(get_session),
            agora: datetime = Depends(agora_utc)) -> VinculoOut:
    try:
        v = svc.aceitar(session, atleta_id, professor_id, corpo.termo_versao, agora)
    except svc.VinculoNaoEncontrado:
        raise HTTPException(status_code=404, detail="vínculo não encontrado") from None
    except svc.TermoDesatualizado:
        raise HTTPException(status_code=409, detail="o termo mudou: leia a versão atual") from None
    session.commit()
    log.info("consentimento aceito: atleta=%s professor=%s", atleta_id, professor_id)
    return VinculoOut(**v.__dict__)


@router.delete("/{professor_id}/consentimento", status_code=204, operation_id="retirarConsentimento", responses={404: _404})
def retirar(atleta_id: int, professor_id: int, session: Session = Depends(get_session), agora: datetime = Depends(agora_utc)) -> Response:
    try:
        svc.revogar(session, atleta_id, professor_id, agora)
    except svc.VinculoNaoEncontrado:
        raise HTTPException(status_code=404, detail="vínculo não encontrado") from None
    session.commit()
    log.info("consentimento retirado: atleta=%s professor=%s", atleta_id, professor_id)
    return Response(status_code=204)


@router_termo.get("/termo-de-consentimento", response_model=TermoOut, operation_id="termoDeConsentimento",
                  responses={401: {"model": Erro, "description": MSG_401}})
def termo(_: ContaAtual = Depends(conta_liberada)) -> TermoOut:
    return TermoOut(versao=svc.TERMO_VIGENTE, provisorio=svc.TERMO_PROVISORIO, texto=svc.TERMO_TEXTO)
