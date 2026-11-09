"""Check-in pos-treino: PUT, GET e DELETE (issue #296, ADR 0012, itens 3, 5 e 7).

Dado pessoal e de saude. Duas regras proprias das rotas de check-in:
- o `422` nao repete o que foi enviado: so `loc`, `msg` e `type` (nem `input`, nem `ctx`); os 422 de dominio saem no mesmo
  formato, com o codigo no `type`. Feito por uma `APIRoute` propria, so deste router (as outras rotas nao mudam);
- nenhum valor do check-in vai para log nem para mensagem de erro: erro inesperado vira `500` com texto fixo e o log leva so ids.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.db.models import CHECKIN_ATALHOS, CHECKIN_TEXTO_MAX, Atividade, Atleta, CheckinTreino
from app.db.session import get_session
from app.rotas.evolucao import Erro
from app.servicos import checkin as svc
from app.servicos.fuso import FUSO_PADRAO, inicio_local

log = logging.getLogger(__name__)

Atalho = Literal["dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse"]


class RotaCheckin(APIRoute):
    """422 sem eco da entrada e 500 sem detalhe, so para as rotas do check-in."""

    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as e:
                detalhe = [{"loc": list(x["loc"]), "msg": x["msg"], "type": x["type"]} for x in e.errors()]
                return JSONResponse(status_code=422, content={"detail": detalhe})
            except HTTPException:
                raise
            except Exception as e:  # noqa: BLE001 - a mensagem de um erro de banco pode trazer os parametros (o texto do check-in)
                log.error("checkin: erro inesperado (%s) em %s", type(e).__name__, request.url.path)
                return JSONResponse(status_code=500, content={"detail": "erro ao processar o check-in"})

        return handler


router = APIRouter(prefix="/atletas/{atleta_id}/atividades/{atividade_id}/checkin", tags=["check-in"], route_class=RotaCheckin)

_RESPOSTAS = {
    404: {"model": Erro, "description": "Atleta, atividade ou (no GET) check-in não encontrados (atividade de outro atleta também)"},
    422: {"description": "Entrada inválida, atividade que não pede check-in ou fora do prazo. Nunca repete o que foi enviado: "
                         "só `loc`, `msg` e `type`"},
}


class CheckinIn(BaseModel):
    pse: int = Field(strict=True, ge=0, le=10)  # CR-10
    sensacao: int = Field(strict=True, ge=1, le=5)
    nada_a_relatar: bool = Field(strict=True)
    atalhos: list[Atalho] = Field(default_factory=list)
    texto: str | None = Field(default=None, max_length=CHECKIN_TEXTO_MAX)

    @field_validator("texto", mode="before")
    @classmethod
    def _apara(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None  # vazio grava NULL
        return v

    @model_validator(mode="after")
    def _coerente(self) -> "CheckinIn":
        # mensagens fixas: nunca com o valor recebido
        if len(set(self.atalhos)) != len(self.atalhos):
            raise ValueError("atalhos repetidos")
        tem_obs = bool(self.atalhos) or self.texto is not None
        if self.nada_a_relatar and tem_obs:
            raise ValueError("nada a relatar não combina com atalho nem texto")
        if not self.nada_a_relatar and not tem_obs:
            raise ValueError("escolha nada a relatar, um atalho ou escreva um texto")
        return self


class AtalhoOut(BaseModel):
    chave: Atalho
    texto: str


class CheckinOut(BaseModel):
    """O check-in do próprio atleta. Dado pessoal e de saúde: só nestas rotas, nunca em lista, série ou exportação."""

    atividade_id: int
    pse: int
    pse_texto: str  # a âncora quando existe ("difícil" para 5), senão o número ("6")
    sensacao: int
    sensacao_texto: str
    nada_a_relatar: bool
    atalhos: list[AtalhoOut]
    texto: str | None
    versao: str
    registrado_em: datetime  # America/Sao_Paulo
    atualizado_em: datetime


def _com_fuso(dt: datetime) -> datetime:
    if dt.tzinfo is None:  # o SQLite devolve sem fuso; o banco guarda UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_PADRAO)


def checkin_out(c: CheckinTreino) -> CheckinOut:
    return CheckinOut(
        atividade_id=c.atividade_id, pse=c.pse, pse_texto=svc.PSE_ANCORA.get(c.pse, str(c.pse)),
        sensacao=c.sensacao, sensacao_texto=svc.SENSACAO_TEXTO[c.sensacao], nada_a_relatar=c.nada_a_relatar,
        atalhos=[AtalhoOut(chave=k, texto=svc.ATALHO_TEXTO[k]) for k in CHECKIN_ATALHOS if getattr(c, k)],
        texto=c.texto, versao=c.versao, registrado_em=_com_fuso(c.registrado_em), atualizado_em=_com_fuso(c.atualizado_em),
    )


def _erro_422(codigo: str, msg: str, campo: str = "atividade_id") -> HTTPException:
    return HTTPException(status_code=422, detail=[{"loc": ["path", campo], "msg": msg, "type": codigo}])


def _atividade_do_atleta(session: Session, atleta_id: int, atividade_id: int) -> Atividade:
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    a = session.get(Atividade, atividade_id)
    if a is None or a.atleta_id != atleta_id:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    return a


@router.put("", response_model=CheckinOut, operation_id="registrarCheckin", responses=_RESPOSTAS)
def registrar_checkin(atleta_id: int, atividade_id: int, corpo: CheckinIn, session: Session = Depends(get_session)) -> CheckinOut:
    """Cria ou substitui o check-in da atividade (um por atividade; `200` nos dois casos). O `PUT` substitui tudo: atalho que não
    vier fica desligado. Criar vale até `PRAZO_DIAS` (7) depois do treino; editar não tem prazo."""
    a = _atividade_do_atleta(session, atleta_id, atividade_id)
    if not svc.elegivel(a):
        raise _erro_422("atividade_sem_checkin", "esta parte do treino multiesporte não pede check-in")
    if svc.checkin_da_atividade(session, atividade_id) is None and not svc.no_prazo(a):
        raise _erro_422("fora_do_prazo", f"o check-in só pode ser criado até {svc.PRAZO_DIAS} dias depois do treino")
    c = svc.gravar_checkin(session, a, svc.DadosCheckin(
        corpo.pse, corpo.sensacao, corpo.nada_a_relatar, tuple(corpo.atalhos), corpo.texto))
    log.info("checkin gravado: atleta=%s atividade=%s atalhos=%s", atleta_id, atividade_id, len(corpo.atalhos))
    return checkin_out(c)


@router.get("", response_model=CheckinOut, operation_id="checkinDaAtividade", responses=_RESPOSTAS)
def checkin_da_atividade(atleta_id: int, atividade_id: int, session: Session = Depends(get_session)) -> CheckinOut:
    """O check-in da atividade, ou `404` ("sem check-in") se a atividade existe e não tem."""
    _atividade_do_atleta(session, atleta_id, atividade_id)
    c = svc.checkin_da_atividade(session, atividade_id)
    if c is None:
        raise HTTPException(status_code=404, detail="sem check-in")
    return checkin_out(c)


@router.delete("", status_code=204, operation_id="apagarCheckin", responses={404: _RESPOSTAS[404]})
def apagar_checkin(atleta_id: int, atividade_id: int, session: Session = Depends(get_session)) -> Response:
    """Remove o check-in (a linha, não só os campos), sem prazo. `204` também quando já não havia (idempotente)."""
    _atividade_do_atleta(session, atleta_id, atividade_id)
    svc.apagar_checkin(session, atividade_id)
    log.info("checkin apagado: atleta=%s atividade=%s", atleta_id, atividade_id)
    return Response(status_code=204)


class PendenteOut(BaseModel):
    """Um treino recente sem check-in. Nenhum campo do check-in: so o que ja e da atividade (titulo nao e dado de saude)."""

    atividade_id: int
    modalidade: str
    data_local: str  # AAAA-MM-DD (ADR 0003)
    hora_local: str  # HH:MM
    duracao: str  # h:mm:ss
    titulo: str  # pronto: "Corrida, 45 min"


class PendentesOut(BaseModel):
    dias: int
    total: int
    pendentes: list[PendenteOut]  # mais recentes primeiro


router_pendentes = APIRouter(prefix="/atletas/{atleta_id}/checkins", tags=["check-in"], route_class=RotaCheckin)


@router_pendentes.get(
    "/pendentes", response_model=PendentesOut, operation_id="listarCheckinsPendentes",
    responses={404: {"model": Erro, "description": "Atleta não encontrado"}, 422: _RESPOSTAS[422]},
)
def listar_checkins_pendentes(
    atleta_id: int,
    dias: int = Query(svc.PRAZO_DIAS, ge=1, le=svc.PRAZO_DIAS, description="Janela em dias, de 1 ao prazo de criação (7)"),
    session: Session = Depends(get_session),
) -> PendentesOut:
    """Treinos do atleta sem check-in com data local em `[hoje - dias, hoje]` (hoje em America/Sao_Paulo), mais recentes primeiro.
    Toda modalidade, menos `multiesporte_pai` e `troca`. Sem nenhum campo do check-in."""
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    itens = []
    for a in svc.pendentes(session, atleta_id, dias):
        local = inicio_local(a.inicio, a.fuso_min)
        itens.append(PendenteOut(
            atividade_id=a.id, modalidade=a.modalidade, data_local=local.date().isoformat(), hora_local=local.strftime("%H:%M"),
            duracao=svc.duracao_hms(a.duracao_s), titulo=svc.titulo(a)))
    return PendentesOut(dias=dias, total=len(itens), pendentes=itens)
