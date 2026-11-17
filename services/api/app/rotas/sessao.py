"""Entrar, sair, quem sou e trocar a senha (issue #499, ADR 0016, itens 3 e 4).

`POST /sessao` e a unica rota de dado sem acesso. 401 uniforme (e-mail inexistente, senha errada e conta desativada), 429 com
`espere_s`. A senha, o e-mail e o token nunca vao a log, a erro nem ao 422 (sem eco da entrada).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.autenticacao import MSG_401, ContaAtual, conta_atual
from app.db.models import Atleta, Conta, Professor, Sessao
from app.db.session import get_session
from app.rotas.checkin import RotaCheckin as _RotaSemEco
from app.rotas.evolucao import Erro
from app.servicos import conta as svc


class RotaSessao(_RotaSemEco):
    """422 sem eco da entrada (a senha digitada nao volta) e 500 neutro."""

    MSG_500 = "erro ao processar o pedido"
    LOG_500 = "sessao"


router = APIRouter(tags=["sessão"], route_class=RotaSessao)


class EntrarIn(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    senha: str = Field(min_length=1, max_length=1000)


class QuemSouOut(BaseModel):
    """Quem esta logado. Um dos dois ids e `null` (um papel por conta)."""

    papel: str  # atleta | professor
    atleta_id: int | None = None
    professor_id: int | None = None
    nome: str
    expira_em: datetime
    troca_de_senha_obrigatoria: bool


class EntrarOut(QuemSouOut):
    token: str  # devolvido uma vez; so o hash fica no servidor


class AcessoOut(BaseModel):
    token: str
    expira_em: datetime


class TrocarSenhaIn(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=1000)
    senha_nova: str = Field(min_length=1, max_length=1000)


class Muitas(BaseModel):
    detail: str
    espere_s: int


def _nome(session: Session, conta: Conta | ContaAtual) -> str:
    if conta.atleta_id is not None:
        return session.get(Atleta, conta.atleta_id).nome
    return session.get(Professor, conta.professor_id).nome


def _papel(conta: Conta | ContaAtual) -> str:
    return "atleta" if conta.atleta_id is not None else "professor"


@router.post(
    "/sessao",
    response_model=EntrarOut,
    operation_id="entrar",
    responses={401: {"model": Erro, "description": "E-mail ou senha incorretos (o mesmo corpo para e-mail inexistente, senha errada e conta desativada)"},
               429: {"model": Muitas, "description": "5 falhas em 15 minutos para o e-mail; `espere_s` segundos e `Retry-After`"}},
)
def entrar(corpo: EntrarIn, session: Session = Depends(get_session)):
    try:
        conta, acesso = svc.entrar(session, corpo.email, corpo.senha)
    except svc.ForcaBruta as e:
        session.commit()
        return JSONResponse(status_code=429, content={"detail": "muitas tentativas", "espere_s": e.espere_s},
                            headers={"Retry-After": str(e.espere_s)})
    except svc.CredencialInvalida:
        session.commit()  # grava a falha (limite de tentativas)
        raise HTTPException(status_code=401, detail="e-mail ou senha incorretos", headers={"WWW-Authenticate": "Bearer"}) from None
    session.commit()
    return EntrarOut(token=acesso.token, expira_em=acesso.expira_em, papel=_papel(conta), atleta_id=conta.atleta_id,
                     professor_id=conta.professor_id, nome=_nome(session, conta),
                     troca_de_senha_obrigatoria=bool(conta.deve_trocar_senha))


@router.get("/sessao", response_model=QuemSouOut, operation_id="quemSou",
            responses={401: {"model": Erro, "description": MSG_401}})
def quem_sou(conta: ContaAtual = Depends(conta_atual), session: Session = Depends(get_session)) -> QuemSouOut:
    return QuemSouOut(papel=_papel(conta), atleta_id=conta.atleta_id, professor_id=conta.professor_id,
                     nome=_nome(session, conta), expira_em=conta.expira_em,
                     troca_de_senha_obrigatoria=conta.deve_trocar_senha)


@router.delete("/sessao", status_code=204, operation_id="sair", responses={401: {"model": Erro, "description": MSG_401}})
def sair(conta: ContaAtual = Depends(conta_atual), session: Session = Depends(get_session)) -> Response:
    svc.sair(session.get(Sessao, conta.sessao_id))
    session.commit()
    return Response(status_code=204)


@router.put(
    "/conta/senha",
    response_model=AcessoOut,
    operation_id="trocarSenha",
    responses={401: {"model": Erro, "description": MSG_401},
               422: {"description": "`senha_atual_incorreta` ou `senha_nova_invalida` (com o motivo em `msg`); nunca repete a senha"}},
)
def trocar_senha(corpo: TrocarSenhaIn, conta: ContaAtual = Depends(conta_atual), session: Session = Depends(get_session)):
    c = session.get(Conta, conta.conta_id)
    try:
        acesso = svc.trocar_senha(session, c, corpo.senha_atual, corpo.senha_nova)
    except svc.SenhaAtualIncorreta:
        return JSONResponse(status_code=422, content={"detail": [{"loc": ["body", "senha_atual"], "msg": "senha atual incorreta",
                                                                   "type": "senha_atual_incorreta"}]})
    except svc.SenhaInvalida as e:
        return JSONResponse(status_code=422, content={"detail": [{"loc": ["body", "senha_nova"], "msg": e.motivo,
                                                                   "type": "senha_nova_invalida"}]})
    session.commit()
    return AcessoOut(token=acesso.token, expira_em=acesso.expira_em)
