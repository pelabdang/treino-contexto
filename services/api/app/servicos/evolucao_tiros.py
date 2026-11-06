"""Classificação das corridas e série de tiros de 1 km por sessão (issues #14 e #168).

Desde a `tiros_1km@5` a série é uma visão dos esforços: lê `bloco_atividade` (ADR 0008, item 8), que
`app.servicos.esforcos.detectar_esforcos` grava. Regra e limites em docs/metricas/tiros-1km.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade, BlocoAtividade
from app.metricas import esforcos as ef
from app.metricas.tiros_1km import (
    VERSAO,
    BlocoEntrada,
    CorridaHistorico,
    PontoSessao,
    SessaoTiros,
    mais_rapido_que_o_habitual,
    pace_habitual,
    serie_por_sessao,
    tiro_de_bloco,
    tiros_de_blocos,
)
from app.servicos.esforcos import detectar_esforcos
from app.servicos.fuso import data_local

log = logging.getLogger(__name__)

ORIGENS_PROTEGIDAS = ("professor", "trainingpeaks")
# Fora da série (continuam guardadas e classificadas): decisão do Angelo, issue #51.
SUBTIPOS_FORA_DA_SERIE = ("esteira",)


def _bloco(b: BlocoAtividade) -> BlocoEntrada:
    return BlocoEntrada(
        ordem=b.ordem, categoria=b.categoria, volta_inicial=b.volta_inicial, volta_final=b.volta_final,
        distancia_m=b.distancia_m, duracao_s=b.duracao_s, fc_media=b.fc_media, faixa=b.faixa,
        parada_apos_s=b.parada_apos_s,
    )  # fmt: skip


def _classificar(ativ: Atividade) -> None:
    """Marca os segmentos a partir dos blocos já gravados: voltas dos tiros, recuperações entre eles, o resto."""
    blocos = [_bloco(b) for b in sorted(ativ.blocos, key=lambda b: b.ordem)]
    resultado = tiros_de_blocos(blocos, ativ.modalidade)
    por_ordem = {b.ordem: b for b in blocos}
    voltas_tiro: set[int] = set()
    for o in resultado.tiros:
        voltas_tiro.update(range(por_ordem[o].volta_inicial, por_ordem[o].volta_final + 1))
    primeira = min((por_ordem[o].volta_inicial for o in resultado.tiros), default=None)
    ultima = max((por_ordem[o].volta_final for o in resultado.tiros), default=None)
    for s in ativ.segmentos:
        if s.ordem in voltas_tiro:
            s.tipo = "tiro"
        elif len(resultado.tiros) >= 2 and primeira < s.ordem < ultima:
            s.tipo = "recuperacao"
        else:
            s.tipo = "volta"
        s.versao_deteccao = resultado.versao

    if ativ.tipo_origem in ORIGENS_PROTEGIDAS or ativ.tipo_confirmado:
        return
    if resultado.eh_intervalado:
        ativ.tipo_treino, ativ.tipo_origem = "intervalado", "sugestao"
    elif ativ.tipo_origem == "sugestao" and ativ.tipo_treino == "intervalado":
        ativ.tipo_treino = ativ.tipo_origem = None  # a regra não sugere mais


def classificar_atividades(session: Session, atleta_id: int) -> int:
    """Detecta os esforços e classifica os segmentos de cada corrida do atleta. Idempotente. Devolve quantas corridas.

    Primeiro roda `detectar_esforcos` (blocos em `bloco_atividade`, `esforcos@1`); depois marca
    `tiro`/`recuperacao`/`volta` nos segmentos pela visão de 1 km e grava `versao_deteccao`. Se é intervalado
    (2 ou mais tiros), sugere `tipo_treino = intervalado` sem sobrescrever o tipo do professor/TrainingPeaks nem
    um tipo confirmado. É também a reclassificação: uma versão nova da regra regrava tudo.
    Falha na detecção de esforços vira aviso no log (não exceção): é o único ponto de detecção da importação.
    """
    try:
        detectar_esforcos(session, atleta_id)
    except Exception:  # noqa: BLE001 - nunca derruba a importacao; reclassificacao_pendente avisa a API
        session.rollback()
        log.warning("esforcos nao detectados; rode worker.detectar_esforcos", exc_info=True)
    ativs = session.scalars(
        select(Atividade)
        .where(Atividade.atleta_id == atleta_id, Atividade.modalidade == "corrida")
        .options(selectinload(Atividade.segmentos), selectinload(Atividade.blocos))
    ).all()
    for a in ativs:
        _classificar(a)
    session.commit()
    return len(ativs)


@dataclass(frozen=True)
class TiroSessao:
    ordem: int  # `segmento.ordem` da primeira volta do tiro
    distancia_m: float | None  # None quando o bloco não tem distância (nunca 0)
    duracao_s: float
    fc_media: float | None


@dataclass(frozen=True)
class SessaoSerie:
    """Um ponto da série com o que a API precisa para detalhar a sessão."""

    ponto: PontoSessao
    inicio: datetime  # horário UTC (com fuso) da atividade
    tiros: tuple[TiroSessao, ...]


def _corridas_da_serie(session: Session, atleta_id: int) -> list[Atividade]:
    """Corridas do atleta que a série considera (fora a esteira), com segmentos e blocos."""
    return list(session.scalars(
        select(Atividade)
        .where(
            Atividade.atleta_id == atleta_id,
            Atividade.modalidade == "corrida",
            or_(Atividade.subtipo.is_(None), Atividade.subtipo.not_in(SUBTIPOS_FORA_DA_SERIE)),
        )
        .options(selectinload(Atividade.segmentos), selectinload(Atividade.blocos))
    ).all())


def sessoes_tiros_1km(
    session: Session, atleta_id: int, inicio: date | None = None, fim: date | None = None
) -> list[SessaoSerie]:
    """Uma sessão por treino com 2 ou mais tiros de 1 km, por data local crescente, com o ponto da série e os tiros.

    `inicio` e `fim` são datas locais (ADR 0003), inclusivas. Lê os blocos já gravados em `bloco_atividade`
    (`tiros_1km@5`, ADR 0008 item 8): os tiros são os esforços da faixa `d1000`, menos os do ritmo parecido e do bloco
    contínuo. Atividades de esteira (`SUBTIPOS_FORA_DA_SERIE`) ficam de fora da série, mas seguem no banco.
    Só entram as sessões cujo pace médio dos tiros é pelo menos 10% mais rápido que o ritmo habitual do atleta; o
    histórico usa todas as corridas do atleta (fora a esteira), mesmo fora de `inicio`/`fim`.
    """
    ativs = _corridas_da_serie(session, atleta_id)
    historico = [
        CorridaHistorico(data_local(a.inicio, a.fuso_min), a.distancia_m or 0.0, a.duracao_s, a.subtipo in SUBTIPOS_FORA_DA_SERIE)
        for a in ativs
    ]
    sessoes, por_id = [], {}
    for a in ativs:
        dia = data_local(a.inicio, a.fuso_min)
        if (inicio and dia < inicio) or (fim and dia > fim):
            continue
        blocos = [_bloco(b) for b in sorted(a.blocos, key=lambda b: b.ordem)]
        resultado = tiros_de_blocos(blocos, a.modalidade)
        por_ordem = {b.ordem: b for b in blocos}
        tiros = tuple(tiro_de_bloco(por_ordem[o]) for o in resultado.tiros)
        sessoes.append(SessaoTiros(a.id, dia, resultado.eh_intervalado, tiros, resultado.versao))
        por_id[a.id] = (a, tiros)
    resultado = []
    for ponto in serie_por_sessao(sessoes):
        if not mais_rapido_que_o_habitual(ponto.pace_s_km, pace_habitual(historico, ponto.data)):
            continue
        a, tiros = por_id[ponto.atividade_id]
        inicio_utc = a.inicio if a.inicio.tzinfo else a.inicio.replace(tzinfo=timezone.utc)
        resultado.append(SessaoSerie(
            ponto, inicio_utc.astimezone(timezone.utc),
            tuple(TiroSessao(t.ordem, t.distancia_m or None, t.duracao_s, t.fc_media) for t in tiros)))
    return resultado


def reclassificacao_pendente(
    session: Session, atleta_id: int, inicio: date | None = None, fim: date | None = None
) -> bool:
    """A série está com dado gravado por outra versão da regra (ADR 0004, item 3)?

    Olha as corridas do atleta que a série considera (fora a esteira, com data local entre `inicio` e `fim`), tenham
    virado tiro ou não. Pendente se algum segmento tem `versao_deteccao` diferente de `VERSAO` (inclui nunca
    classificado) ou se algum bloco foi gravado por outra versão dos esforços (`esforcos.VERSAO`). Só lê; não escreve.
    """
    for a in _corridas_da_serie(session, atleta_id):
        dia = data_local(a.inicio, a.fuso_min)
        if (inicio and dia < inicio) or (fim and dia > fim):
            continue
        if any(s.versao_deteccao != VERSAO for s in a.segmentos):
            return True
        if any(b.versao_deteccao != ef.VERSAO for b in a.blocos):
            return True
    return False


def serie_tiros_1km(
    session: Session, atleta_id: int, inicio: date | None = None, fim: date | None = None
) -> list[PontoSessao]:
    """Um ponto por sessão com tiros de 1 km (pace e FC médios, melhor tiro), por data local crescente."""
    return [s.ponto for s in sessoes_tiros_1km(session, atleta_id, inicio, fim)]
