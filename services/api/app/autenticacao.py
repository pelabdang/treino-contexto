"""Quem esta chamando (issue #499, ADR 0016, itens 3 e 5): o acesso vem no cabecalho `Authorization: Bearer <token>`, sem cookie.

`conta_atual`: 401 sem acesso valido (ausente, errado, expirado, revogado ou conta desativada), sempre o mesmo corpo.
`conta_liberada`: o mesmo, mais o 403 `troca_de_senha_obrigatoria` enquanto a senha provisoria nao foi trocada; e o que as rotas de dado
usam (#500). Nada daqui escreve o token, o e-mail ou a senha em log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.servicos import conta as svc

_bearer = HTTPBearer(auto_error=False, description="Acesso devolvido por `POST /sessao`")

MSG_401 = "não autenticado"
PROFESSOR_INEXISTENTE = {
    "detail": [{"loc": ["path", "professor_id"], "msg": "professor inexistente", "type": "professor_inexistente"}]
}
MSG_TROCA = "troque a senha provisória para continuar"


@dataclass(frozen=True)
class ContaAtual:
    conta_id: int
    atleta_id: int | None
    professor_id: int | None
    deve_trocar_senha: bool
    sessao_id: int
    expira_em: datetime


def nao_autenticado() -> HTTPException:
    return HTTPException(status_code=401, detail=MSG_401, headers={"WWW-Authenticate": "Bearer"})


def conta_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
                session: Session = Depends(get_session)) -> ContaAtual:
    if credenciais is None or not credenciais.credentials:
        raise nao_autenticado()
    achou = svc.conta_da_sessao(session, credenciais.credentials)
    if achou is None:
        raise nao_autenticado()
    conta, sessao = achou
    return ContaAtual(conta.id, conta.atleta_id, conta.professor_id, bool(conta.deve_trocar_senha), sessao.id, sessao.expira_em)


def conta_liberada(conta: ContaAtual = Depends(conta_atual)) -> ContaAtual:
    if conta.deve_trocar_senha:
        raise HTTPException(status_code=403, detail=[{"loc": [], "msg": MSG_TROCA, "type": "troca_de_senha_obrigatoria"}])
    return conta


def atleta_da_sessao(atleta_id: int, conta: ContaAtual = Depends(conta_liberada)) -> int:
    """Rotas `/atletas/{atleta_id}/...` (ADR 0016, item 5): so a conta cujo `atleta_id` e o do caminho. Outro id, ou conta de professor,
    responde o MESMO 404 de atleta inexistente (nunca 403). Devolve o id da SESSAO."""
    if conta.atleta_id is None or conta.atleta_id != atleta_id:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    return conta.atleta_id


def professor_da_sessao(professor_id: int, conta: ContaAtual = Depends(conta_liberada)) -> int:
    """Rotas `/professores/{professor_id}/...`: so a conta cujo `professor_id` e o do caminho; qualquer outro id da o 404 uniforme
    `professor_inexistente` (ADR 0015, item 2). Devolve o id da SESSAO, nunca o do caminho."""
    if conta.professor_id is None or conta.professor_id != professor_id:
        raise HTTPException(status_code=404, detail=PROFESSOR_INEXISTENTE["detail"])
    return conta.professor_id
