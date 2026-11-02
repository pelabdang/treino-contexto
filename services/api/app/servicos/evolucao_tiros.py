"""Classificação das corridas e série de tiros de 1 km por sessão (issue #14).

Liga as funções puras de `app.metricas.tiros_1km` ao banco. Regra e limites em docs/metricas/tiros-1km.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade, Segmento
from app.metricas.tiros_1km import (
    MIN_TIROS_INTERVALADO,
    VERSAO,
    PontoSessao,
    SessaoTiros,
    VoltaEntrada,
    detectar_tiros,
    serie_por_sessao,
)
from app.servicos.fuso import data_local

ORIGENS_PROTEGIDAS = ("professor", "trainingpeaks")
# Fora da série (continuam guardadas e classificadas): decisão do Angelo, issue #51.
SUBTIPOS_FORA_DA_SERIE = ("esteira",)


def _volta(s: Segmento) -> VoltaEntrada:
    return VoltaEntrada(
        ordem=s.ordem,
        distancia_m=s.distancia_m or 0.0,
        duracao_s=s.duracao_s,
        fc_media=s.fc_media,
        intensidade=s.intensidade,
    )


def _classificar(ativ: Atividade) -> None:
    resultado = detectar_tiros([_volta(s) for s in ativ.segmentos], ativ.modalidade)
    tiros, recuperacoes = set(resultado.tiros), set(resultado.recuperacoes)
    for s in ativ.segmentos:
        s.tipo = "tiro" if s.ordem in tiros else "recuperacao" if s.ordem in recuperacoes else "volta"
        s.versao_deteccao = resultado.versao

    if ativ.tipo_origem in ORIGENS_PROTEGIDAS or ativ.tipo_confirmado:
        return
    if resultado.eh_intervalado:
        ativ.tipo_treino, ativ.tipo_origem = "intervalado", "sugestao"
    elif ativ.tipo_origem == "sugestao" and ativ.tipo_treino == "intervalado":
        ativ.tipo_treino = ativ.tipo_origem = None  # a regra não sugere mais


def classificar_atividades(session: Session, atleta_id: int) -> int:
    """Classifica os segmentos de cada corrida do atleta. Idempotente. Devolve quantas corridas processou.

    Marca `tiro`/`recuperacao`/`volta` e grava `versao_deteccao`. Se é intervalado, sugere
    `tipo_treino = intervalado` sem sobrescrever o tipo do professor/TrainingPeaks nem um tipo confirmado.
    """
    ativs = session.scalars(
        select(Atividade)
        .where(Atividade.atleta_id == atleta_id, Atividade.modalidade == "corrida")
        .options(selectinload(Atividade.segmentos))
    ).all()
    for a in ativs:
        _classificar(a)
    session.commit()
    return len(ativs)


@dataclass(frozen=True)
class TiroSessao:
    ordem: int
    distancia_m: float
    duracao_s: float
    fc_media: float | None


@dataclass(frozen=True)
class SessaoSerie:
    """Um ponto da série com o que a API precisa para detalhar a sessão."""

    ponto: PontoSessao
    inicio: datetime  # horário UTC (com fuso) da atividade
    tiros: tuple[TiroSessao, ...]


def sessoes_tiros_1km(
    session: Session, atleta_id: int, inicio: date | None = None, fim: date | None = None
) -> list[SessaoSerie]:
    """Uma sessão por treino intervalado, por data local crescente, com o ponto da série e os tiros.

    `inicio` e `fim` são datas locais (ADR 0003), inclusivas. Lê os segmentos já classificados.
    Atividades de esteira (`SUBTIPOS_FORA_DA_SERIE`) ficam de fora da série, mas seguem no banco.
    """
    ativs = session.scalars(
        select(Atividade)
        .where(
            Atividade.atleta_id == atleta_id,
            Atividade.modalidade == "corrida",
            or_(Atividade.subtipo.is_(None), Atividade.subtipo.not_in(SUBTIPOS_FORA_DA_SERIE)),
        )
        .options(selectinload(Atividade.segmentos))
    ).all()
    sessoes, por_id = [], {}
    for a in ativs:
        dia = data_local(a.inicio, a.fuso_min)
        if (inicio and dia < inicio) or (fim and dia > fim):
            continue
        segs = sorted((s for s in a.segmentos if s.tipo == "tiro"), key=lambda s: s.ordem)
        tiros = tuple(_volta(s) for s in segs)
        versao = next((s.versao_deteccao for s in segs if s.versao_deteccao), VERSAO)
        sessoes.append(SessaoTiros(a.id, dia, len(tiros) >= MIN_TIROS_INTERVALADO, tiros, versao))
        por_id[a.id] = (a, segs)
    resultado = []
    for ponto in serie_por_sessao(sessoes):
        a, segs = por_id[ponto.atividade_id]
        inicio_utc = a.inicio if a.inicio.tzinfo else a.inicio.replace(tzinfo=timezone.utc)
        resultado.append(SessaoSerie(
            ponto, inicio_utc.astimezone(timezone.utc),
            tuple(TiroSessao(s.ordem, s.distancia_m or 0.0, s.duracao_s, s.fc_media) for s in segs)))
    return resultado


def serie_tiros_1km(
    session: Session, atleta_id: int, inicio: date | None = None, fim: date | None = None
) -> list[PontoSessao]:
    """Um ponto por sessão intervalada (pace e FC médios dos tiros), por data local crescente."""
    return [s.ponto for s in sessoes_tiros_1km(session, atleta_id, inicio, fim)]
