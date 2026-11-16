"""`GET /professores/{professor_id}/caixa-do-dia` (issue #424, ADR 0015 itens 3 a 7, adendo da ADR 0004).

A caixa e CALCULADA a cada leitura (nada guardado): os alunos do professor ordenados por `atencao@1` (`metricas/atencao.py`) e os
treinos novos com tipo sugerido. A API formata, o app mostra (ADR 0004, adendo 2): o app nao ordena, nao escolhe janela nem monta frase.

Regras de privacidade (ADR 0015, itens 3 e 7):
- O unico filtro de atleta e `atletas_do_professor` (vinculo E consentimento ate `agora`); nenhuma consulta de atividade, check-in ou
  feedback acontece fora dele. O id do professor e o da CONFIGURACAO (`professor_da_rota`).
- A observacao livre do check-in so existe em `detalhe.checkin.observacao`: nunca entra na `atencao@1` (a funcao nem recebe o campo),
  nunca vai a um modelo de linguagem (esta rota nao chama nenhum) e nunca vai a log. O log leva so `professor_id` e contagens.
- `Cache-Control: no-store`: a resposta tem dado de saude.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import get_session
from app.metricas import atencao as at
from app.rotas.atividades import FeedbackOut, _feedback, _feedback_out
from app.rotas.checkin import AtalhoOut, RotaCheckin, checkin_out
from app.rotas.evolucao import Erro
from app.servicos.carga_pse_leitura import duracao_pt
from app.servicos.fuso import FUSO_PADRAO, data_local, inicio_local
from app.servicos.linha_base_leitura import linha_base_resultado
from app.servicos.professor import agora_utc, atletas_do_professor, professor_da_rota

log = logging.getLogger(__name__)

router = APIRouter(prefix="/professores/{professor_id}", tags=["professor"], route_class=RotaCheckin)

TIPO_TEXTO = {"leve": "Leve", "moderado": "Moderado", "longo": "Longo", "intervalado": "Intervalado", "fartlek": "Fartlek"}
ORIGEM_TEXTO = {
    "sugestao": "sugerido pela regra",
    "semana_padrao": "sugerido pela semana-padrão",
    "professor": "definido pelo professor",
    "trainingpeaks": "vindo do TrainingPeaks",
}
Modalidade = Literal["corrida", "ciclismo", "natacao"]


class MotivoOut(BaseModel):
    codigo: Literal["dor", "fora_do_normal", "divergencia", "checkin_vencendo"]
    texto: str


class CheckinDetalheOut(BaseModel):
    pse_texto: str
    sensacao: int
    sensacao_texto: str
    atalhos: list[AtalhoOut]
    nada_a_relatar: bool
    observacao: str | None  # a observacao livre do atleta: so aqui, nunca em lista, log ou modelo


class DetalheOut(BaseModel):
    tipo_texto: str | None  # null: treino sem tipo
    tipo_origem_texto: str | None
    tipo_confirmado: bool
    checkin: CheckinDetalheOut | None  # null: sem check-in
    feedback: FeedbackOut | None  # null em multiesporte_pai e troca


class TreinoBase(BaseModel):
    atividade_id: int
    modalidade: Modalidade
    data_local: str  # AAAA-MM-DD
    hora_local: str  # HH:MM
    duracao_texto: str  # "45 min"
    detalhe: DetalheOut


class TreinoComMotivoOut(TreinoBase):
    motivos: list[MotivoOut]


class AlunoOut(BaseModel):
    atleta_id: int
    nome: str
    sem_motivo: bool
    texto_sem_motivo: str | None  # so quando `sem_motivo`
    treinos: list[TreinoComMotivoOut]  # so os treinos com motivo, do mais recente ao mais antigo


class NovoOut(TreinoBase):
    atleta_id: int
    atleta_nome: str
    tipo_sugerido: Literal["leve", "moderado", "longo", "intervalado", "fartlek"]
    tipo_sugerido_texto: str
    origem_texto: str


class CaixaDoDiaOut(BaseModel):
    versao: str
    hoje: str  # AAAA-MM-DD, America/Sao_Paulo: a mesma data das janelas
    janela_atencao_dias: int
    janela_novos_dias: int
    alunos: list[AlunoOut]
    novos: list[NovoOut]  # mais recente primeiro


def _detalhe(session: Session, a: Atividade) -> DetalheOut:
    c = a.checkin
    checkin = None
    if c is not None:
        o = checkin_out(c)
        checkin = CheckinDetalheOut(pse_texto=o.pse_texto, sensacao=o.sensacao, sensacao_texto=o.sensacao_texto, atalhos=o.atalhos,
                                    nada_a_relatar=o.nada_a_relatar, observacao=o.texto)
    return DetalheOut(
        tipo_texto=TIPO_TEXTO.get(a.tipo_treino) if a.tipo_treino else None,
        tipo_origem_texto=ORIGEM_TEXTO.get(a.tipo_origem) if a.tipo_treino and a.tipo_origem else None,
        tipo_confirmado=bool(a.tipo_confirmado),
        checkin=checkin,
        feedback=_feedback_out(_feedback(session, a)),
    )


def _campos(session: Session, a: Atividade) -> dict:
    local = inicio_local(a.inicio, a.fuso_min)
    return dict(atividade_id=a.id, modalidade=a.modalidade, data_local=local.date().isoformat(), hora_local=local.strftime("%H:%M"),
                duracao_texto=duracao_pt(a.duracao_s / 60), detalhe=_detalhe(session, a))


def _treino_atencao(session: Session, a: Atividade, dia: date, hoje: date) -> at.TreinoAtencao:
    fora: tuple[tuple[str, float], ...] = ()
    if 0 <= (hoje - dia).days <= at.JANELA_DIAS:  # a linha de base so pesa dentro da janela da atencao
        lb = linha_base_resultado(session, a)
        if lb.estado == "ok":
            fora = tuple((m.chave, m.z) for m in lb.metricas if m.estado == "fora" and m.z is not None)
    return at.TreinoAtencao(
        id=a.id, dia=dia, modalidade=a.modalidade, subtipo=a.subtipo, tipo_treino=a.tipo_treino, tipo_origem=a.tipo_origem,
        tipo_confirmado=bool(a.tipo_confirmado), tipo_divergencia=a.tipo_divergencia, metricas_fora=fora,
        dor=None if a.checkin is None else bool(a.checkin.dor),
    )


def montar_caixa(session: Session, professor_id: int, agora: datetime) -> CaixaDoDiaOut:
    hoje = agora.astimezone(FUSO_PADRAO).date()
    visiveis = atletas_do_professor(professor_id, agora)  # o unico filtro de atleta
    atletas = session.scalars(select(Atleta).where(Atleta.id.in_(visiveis)).order_by(Atleta.id)).all()
    corte = hoje - timedelta(days=at.JANELA_NOVOS_DIAS + 1)  # folga de um dia para o fuso; a data local exata e conferida abaixo
    ativs = session.scalars(
        select(Atividade)
        .where(Atividade.atleta_id.in_(visiveis), Atividade.inicio >= datetime(corte.year, corte.month, corte.day, tzinfo=agora.tzinfo))
        .options(joinedload(Atividade.checkin).joinedload(CheckinTreino.feedback), selectinload(Atividade.blocos),
                 selectinload(Atividade.carga), selectinload(Atividade.rotulo_transicao))
    ).unique().all()

    por_atleta: dict[int, list[tuple[Atividade, date]]] = {x.id: [] for x in atletas}
    for a in ativs:
        dia = data_local(a.inicio, a.fuso_min)
        if 0 <= (hoje - dia).days <= at.JANELA_NOVOS_DIAS:
            por_atleta[a.atleta_id].append((a, dia))
    por_id = {a.id: a for a, _ in (p for lista in por_atleta.values() for p in lista)}

    entradas = {aid: [_treino_atencao(session, a, dia, hoje) for a, dia in lista] for aid, lista in por_atleta.items()}
    resultado = at.atencao(entradas, hoje)
    nomes = {x.id: x.nome for x in atletas}

    alunos: list[AlunoOut] = []
    for item in resultado.com_atencao:
        treinos = [TreinoComMotivoOut(**_campos(session, por_id[t.id]), motivos=[MotivoOut(codigo=m.codigo, texto=m.texto) for m in t.motivos])
                   for t in item.treinos]
        alunos.append(AlunoOut(atleta_id=item.atleta, nome=nomes[item.atleta], sem_motivo=False, texto_sem_motivo=None, treinos=treinos))
    for aid in resultado.sem_atencao:
        alunos.append(AlunoOut(atleta_id=aid, nome=nomes[aid], sem_motivo=True, texto_sem_motivo=resultado.sem_atencao_texto, treinos=[]))

    todos = [t for lista in entradas.values() for t in lista]
    todos.sort(key=lambda t: (t.dia, por_id[t.id].inicio.replace(tzinfo=None)), reverse=True)  # mais recente primeiro
    novos = []
    for tid in at.treinos_novos(todos, hoje):
        a = por_id[tid]
        novos.append(NovoOut(**_campos(session, a), atleta_id=a.atleta_id, atleta_nome=nomes[a.atleta_id], tipo_sugerido=a.tipo_treino,
                             tipo_sugerido_texto=TIPO_TEXTO[a.tipo_treino], origem_texto=ORIGEM_TEXTO[a.tipo_origem]))
    log.info("caixa-do-dia: professor=%s alunos=%s com_motivo=%s novos=%s", professor_id, len(alunos), len(resultado.com_atencao), len(novos))
    return CaixaDoDiaOut(versao=resultado.versao, hoje=hoje.isoformat(), janela_atencao_dias=at.JANELA_DIAS,
                         janela_novos_dias=at.JANELA_NOVOS_DIAS, alunos=alunos, novos=novos)


@router.get(
    "/caixa-do-dia",
    response_model=CaixaDoDiaOut,
    operation_id="buscarCaixaDoDia",
    responses={404: {"model": Erro, "description": "Professor inexistente (`professor_inexistente`, uniforme: sem configuracao, id diferente "
                                                    "do configurado ou sem linha)"}},
)
def buscar_caixa_do_dia(
    response: Response,
    professor_id: int = Depends(professor_da_rota),
    session: Session = Depends(get_session),
    agora: datetime = Depends(agora_utc),
) -> CaixaDoDiaOut:
    """Os alunos do professor com consentimento, por `atencao@1`, e os treinos novos com tipo sugerido (calculado a cada leitura)."""
    response.headers["Cache-Control"] = "no-store"
    return montar_caixa(session, professor_id, agora)
