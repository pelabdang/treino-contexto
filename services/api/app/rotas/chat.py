"""Chat do atleta: conversas e mensagens (#598, ADR 0017, itens 7 e 8; adendo 16 da ADR 0004).

Todas as rotas entram por `/atletas/{atleta_id}` e passam por `atleta_da_sessao` (ADR 0016, item 5): id de outro, de professor ou inexistente
responde o MESMO 404. Conversa de outro atleta e conversa inexistente tambem. O professor nunca chega aqui.
Sincrono (sem streaming): o texto so aparece depois das checagens. Pergunta, resultado de ferramenta e resposta sao dado de saude: o 422 nao
repete o que foi enviado, o 500 tem texto fixo e nada disso vai para log. Texto reprovado nunca e gravado nem devolvido.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import app.chat  # noqa: F401  (registra as ferramentas)
from app.autenticacao import ContaAtual, conta_liberada
from app.chat import laco, prompt
from app.chat.registro import Consulta, Quem, executar
from app.db.models import CHAT_PERGUNTA_MAX, CHAT_TITULO_MAX, Conversa, Mensagem
from app.db.session import get_session
from app.explicacao import checagens_chat as ck
from app.llm.camada import Redator, criar_redator
from app.rotas.checkin import RotaCheckin
from app.rotas.evolucao import Erro
from app.servicos.checkin import hoje_local
from app.servicos.fuso import FUSO_PADRAO

log = logging.getLogger(__name__)

PERGUNTAS_POR_HORA = 20  # por atleta (ADR 0017, "A confirmar" 5); conta as linhas de `mensagem`, vale com varias instancias
FRASE_ERRO = "Não consegui responder agora. Tente de novo em instantes."
FRASE_LIMITE = "Você já fez muitas perguntas nesta hora. Tente de novo em alguns minutos."
MAX_LINKS = 5


class RotaChat(RotaCheckin):
    MSG_500 = "erro ao processar a conversa"
    LOG_500 = "chat"


router = APIRouter(prefix="/atletas/{atleta_id}/conversas", tags=["chat"], route_class=RotaChat)

_404 = {404: {"model": Erro, "description": "Atleta, conversa ou mensagem de outro (o mesmo 404 de inexistente)"}}
_422 = {422: {"description": "Pergunta vazia ou grande demais. Nunca repete o que foi enviado: so `loc`, `msg` e `type`"}}


def get_redator() -> Redator:
    """Um `Redator` por pergunta (o limite de chamadas da instancia vale por pergunta). Os testes trocam por um provedor falso."""
    return criar_redator()


class PerguntaIn(BaseModel):
    pergunta: str = Field(max_length=CHAT_PERGUNTA_MAX)

    @field_validator("pergunta")
    @classmethod
    def _nao_vazia(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("a pergunta não pode ser vazia")  # mensagem fixa, sem o valor
        return v


class LinkOut(BaseModel):
    tipo: Literal["treino", "evolucao"]
    rotulo: str  # "Abrir treino" ou "Abrir na Evolução"
    atividade_id: int | None = None
    serie_id: str | None = None


class MensagemOut(BaseModel):
    id: int
    ordem: int
    pergunta: str
    estado: Literal["respondida", "recusada", "reprovada", "erro"]
    motivo: str | None  # codigo; so em recusada, reprovada e erro
    texto: str  # o que o app mostra: a resposta aprovada, o texto fixo da recusa ou a frase fixa de erro
    links: list[LinkOut]
    criada_em: datetime  # America/Sao_Paulo


class ConversaResumoOut(BaseModel):
    id: int
    titulo: str
    criada_em: datetime
    atualizada_em: datetime


class ConversaOut(ConversaResumoOut):
    mensagens: list[MensagemOut]


class ListaConversasOut(BaseModel):
    atleta_id: int
    conversas: list[ConversaResumoOut]


class Muitas(BaseModel):
    detail: str
    espere_s: int


def _com_fuso(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_PADRAO)


def _links(m: Mensagem) -> list[LinkOut]:
    """Links montados pelo CODIGO a partir dos ids que apareceram nos resultados das ferramentas da pergunta e que o texto realmente cita
    (a data do treino). O modelo nao escreve link. Serie: o `serie_id` de um resultado usado na resposta."""
    if m.estado != "respondida" or not m.resposta:
        return []
    treinos: list[LinkOut] = []
    series: list[LinkOut] = []

    def percorrer(x):
        if isinstance(x, dict):
            aid, data = x.get("atividade_id"), x.get("data_texto")
            if isinstance(aid, int) and isinstance(data, str) and data in m.resposta and aid not in {l.atividade_id for l in treinos}:
                treinos.append(LinkOut(tipo="treino", rotulo="Abrir treino", atividade_id=aid))
            sid = x.get("serie_id")
            if isinstance(sid, str) and sid not in {l.serie_id for l in series}:
                series.append(LinkOut(tipo="evolucao", rotulo="Abrir na Evolução", serie_id=sid))
            for v in x.values():
                percorrer(v)
        elif isinstance(x, list):
            for v in x:
                percorrer(v)

    for c in m.chamadas_ferramenta or []:
        percorrer(c.get("resultado"))
    return (treinos + series)[:MAX_LINKS]


def _mensagem_out(m: Mensagem) -> MensagemOut:
    texto = m.resposta if m.resposta else FRASE_ERRO
    return MensagemOut(id=m.id, ordem=m.ordem, pergunta=m.pergunta, estado=m.estado, motivo=m.motivo, texto=texto, links=_links(m),
                       criada_em=_com_fuso(m.criada_em))


def _resumo(c: Conversa) -> dict:
    return dict(id=c.id, titulo=c.titulo, criada_em=_com_fuso(c.criada_em), atualizada_em=_com_fuso(c.atualizada_em))


def _conversa_do_atleta(session: Session, atleta_id: int, conversa_id: int) -> Conversa:
    c = session.scalar(select(Conversa).where(Conversa.id == conversa_id, Conversa.atleta_id == atleta_id, Conversa.dono_papel == "atleta"))
    if c is None:
        raise HTTPException(status_code=404, detail="conversa não encontrada")
    return c


def _espera_do_limite(session: Session, atleta_id: int, agora: datetime) -> int | None:
    """Segundos ate liberar uma pergunta, se o atleta ja fez 20 na ultima hora; `None` se pode perguntar."""
    desde = agora - timedelta(hours=1)
    q = (select(Mensagem.criada_em).join(Conversa, Conversa.id == Mensagem.conversa_id)
         .where(Conversa.atleta_id == atleta_id, Mensagem.criada_em > desde).order_by(Mensagem.criada_em.desc()).limit(PERGUNTAS_POR_HORA))
    horas = session.scalars(q).all()
    if len(horas) < PERGUNTAS_POR_HORA:
        return None
    mais_antiga = horas[-1] if horas[-1].tzinfo else horas[-1].replace(tzinfo=timezone.utc)
    return max(1, int((mais_antiga + timedelta(hours=1) - agora).total_seconds()) + 1)


def _historico(session: Session, conversa_id: int) -> list[tuple[str, str]]:
    """As trocas APROVADAS (respondidas) da conversa; nunca texto reprovado nem resultado de ferramenta antigo."""
    linhas = session.execute(select(Mensagem.pergunta, Mensagem.resposta).where(Mensagem.conversa_id == conversa_id, Mensagem.estado == "respondida")
                             .order_by(Mensagem.ordem)).all()
    return [(p, r) for p, r in linhas]


def _responder_e_gravar(session: Session, redator: Redator, conta: ContaAtual, atleta_id: int, conversa: Conversa, pergunta: str) -> Mensagem:
    historico = _historico(session, conversa.id) if conversa.id is not None else []
    consulta = Consulta(Quem("atleta", conta.conta_id), atleta_id, hoje_local())
    r = laco.responder(redator, lambda nome, args: executar(session, consulta, nome, args), consulta, pergunta, historico)
    ordem = 1 if conversa.id is None else (session.scalar(select(func.max(Mensagem.ordem)).where(Mensagem.conversa_id == conversa.id)) or 0) + 1
    motivo = r.motivo if r.estado != "respondida" else None
    if r.estado in ("reprovada", "erro", "recusada") and not motivo:
        motivo = "provedor_erro"
    m = Mensagem(
        ordem=ordem, pergunta=pergunta, chamadas_ferramenta=r.chamadas_ferramenta, resposta=r.resposta if r.estado in ("respondida", "recusada") else None,
        estado=r.estado, motivo=motivo, versao_checagens=ck.VERSAO, versao_prompt=prompt.VERSAO, provedor=r.provedor, modelo=r.modelo,
    )
    m.conversa = conversa
    return m


def _checar_limite(session: Session, atleta_id: int):
    espera = _espera_do_limite(session, atleta_id, datetime.now(timezone.utc))
    if espera is None:
        return None
    return JSONResponse(status_code=429, content={"detail": FRASE_LIMITE, "espere_s": espera}, headers={"Retry-After": str(espera)})


@router.post("", response_model=ConversaOut, status_code=201, operation_id="criarConversa", responses={**_404, **_422,
             429: {"model": Muitas, "description": "20 perguntas por hora por atleta; `espere_s` e `Retry-After` em segundos"}})
def criar_conversa(atleta_id: int, corpo: PerguntaIn, conta: ContaAtual = Depends(conta_liberada), session: Session = Depends(get_session),
                   redator: Redator = Depends(get_redator)):
    """Abre uma conversa com a primeira pergunta e a responde (sincrono, sem streaming). O titulo e a pergunta cortada, sem passar pelo provedor."""
    if (limite := _checar_limite(session, atleta_id)) is not None:
        return limite
    agora = datetime.now(timezone.utc)
    conversa = Conversa(atleta_id=atleta_id, dono_papel="atleta", dono_conta_id=conta.conta_id, titulo=corpo.pergunta[:CHAT_TITULO_MAX],
                        criada_em=agora, atualizada_em=agora)
    m = _responder_e_gravar(session, redator, conta, atleta_id, conversa, corpo.pergunta)
    session.add(conversa)
    session.commit()
    return ConversaOut(**_resumo(conversa), mensagens=[_mensagem_out(m)])


@router.post("/{conversa_id}/mensagens", response_model=MensagemOut, operation_id="enviarMensagem", responses={**_404, **_422,
             429: {"model": Muitas, "description": "20 perguntas por hora por atleta; `espere_s` e `Retry-After` em segundos"}})
def enviar_mensagem(atleta_id: int, conversa_id: int, corpo: PerguntaIn, conta: ContaAtual = Depends(conta_liberada),
                    session: Session = Depends(get_session), redator: Redator = Depends(get_redator)):
    """Continua uma conversa: a pergunta e a resposta de uma vez (sincrono)."""
    conversa = _conversa_do_atleta(session, atleta_id, conversa_id)
    if (limite := _checar_limite(session, atleta_id)) is not None:
        return limite
    m = _responder_e_gravar(session, redator, conta, atleta_id, conversa, corpo.pergunta)
    conversa.atualizada_em = datetime.now(timezone.utc)
    session.add(m)
    session.commit()
    return _mensagem_out(m)


@router.get("", response_model=ListaConversasOut, operation_id="listarConversas", responses=_404)
def listar_conversas(atleta_id: int, limite: int = Query(50, ge=1, le=100), session: Session = Depends(get_session)):
    """As conversas do atleta, da mais recente para a mais antiga (so as dele)."""
    q = (select(Conversa).where(Conversa.atleta_id == atleta_id, Conversa.dono_papel == "atleta")
         .order_by(Conversa.atualizada_em.desc(), Conversa.id.desc()).limit(limite))
    return ListaConversasOut(atleta_id=atleta_id, conversas=[ConversaResumoOut(**_resumo(c)) for c in session.scalars(q)])


@router.get("/{conversa_id}", response_model=ConversaOut, operation_id="buscarConversa", responses=_404)
def buscar_conversa(atleta_id: int, conversa_id: int, session: Session = Depends(get_session)):
    c = _conversa_do_atleta(session, atleta_id, conversa_id)
    return ConversaOut(**_resumo(c), mensagens=[_mensagem_out(m) for m in c.mensagens])


@router.delete("/{conversa_id}", status_code=204, operation_id="apagarConversa", responses=_404)
def apagar_conversa(atleta_id: int, conversa_id: int, session: Session = Depends(get_session)) -> Response:
    """Apaga a conversa e as mensagens dela (a pedido do atleta)."""
    c = _conversa_do_atleta(session, atleta_id, conversa_id)
    session.execute(delete(Mensagem).where(Mensagem.conversa_id == c.id))  # explicito: o SQLite dos testes nao aplica o ON DELETE CASCADE
    session.delete(c)
    session.commit()
    return Response(status_code=204)
