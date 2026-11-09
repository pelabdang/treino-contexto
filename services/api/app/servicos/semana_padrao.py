"""Semana-padrao do atleta: ler a vigencia e gravar (ADR 0011, itens 1, 8 e 9). Plano de treino: dado pessoal, nunca em log."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.db.models import SemanaPadrao, SemanaPadraoItem
from app.servicos.fuso import FUSO_PADRAO
from app.servicos.tipo_treino import aplicar_tipos
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as _insert_pg
from sqlalchemy.dialects.sqlite import insert as _insert_sqlite
from sqlalchemy.orm import Session

_INSERT = {"postgresql": _insert_pg, "sqlite": _insert_sqlite}


@dataclass(frozen=True)
class ItemNovo:
    dia_semana: int
    modalidade: str
    tipo_treino: str | None


@dataclass(frozen=True)
class VigenciaResumo:
    vigente_desde: date
    definido_por: str
    total_itens: int


def hoje_local() -> date:
    """Hoje no calendario de `America/Sao_Paulo` (padrao do `em` do GET)."""
    return datetime.now(FUSO_PADRAO).date()


def vigente_em(session: Session, atleta_id: int, em: date) -> SemanaPadrao | None:
    """Linha de maior `vigente_desde <= em` (mesma regra do limiar, ADR 0010). Nunca olha a vigencia seguinte."""
    return session.scalars(
        select(SemanaPadrao)
        .where(SemanaPadrao.atleta_id == atleta_id, SemanaPadrao.vigente_desde <= em)
        .order_by(SemanaPadrao.vigente_desde.desc())
        .limit(1)
    ).first()


def vigencias(session: Session, atleta_id: int) -> list[VigenciaResumo]:
    """Todas as vigencias do atleta, da mais nova para a mais antiga."""
    total = (
        select(SemanaPadraoItem.semana_padrao_id, func.count().label("n"))
        .group_by(SemanaPadraoItem.semana_padrao_id)
        .subquery()
    )
    linhas = session.execute(
        select(SemanaPadrao.vigente_desde, SemanaPadrao.definido_por, func.coalesce(total.c.n, 0))
        .outerjoin(total, total.c.semana_padrao_id == SemanaPadrao.id)
        .where(SemanaPadrao.atleta_id == atleta_id)
        .order_by(SemanaPadrao.vigente_desde.desc())
    ).all()
    return [VigenciaResumo(d, por, int(n)) for d, por, n in linhas]


def _buscar(session: Session, atleta_id: int, vigente_desde: date) -> SemanaPadrao | None:
    return session.scalars(
        select(SemanaPadrao).where(SemanaPadrao.atleta_id == atleta_id, SemanaPadrao.vigente_desde == vigente_desde)
    ).first()


def _criar_ou_buscar(session: Session, atleta_id: int, vigente_desde: date, definido_por: str, agora: datetime) -> SemanaPadrao:
    """Upsert do cabecalho. Dois PUT concorrentes da mesma vigencia: o que perde a corrida bate no
    `UNIQUE (atleta_id, vigente_desde)`; o `ON CONFLICT DO NOTHING` nao falha, so nao insere, e a busca seguinte acha a
    linha do outro PUT e a atualiza (ADR 0011, item 8). No Postgres o INSERT do segundo espera o commit do primeiro.
    Sem savepoint de proposito: o `SAVEPOINT` do pysqlite commita a transacao externa no `RELEASE`, e o rollback
    do PUT inteiro (reaplicacao da #265) deixaria de valer no SQLite."""
    linha = _buscar(session, atleta_id, vigente_desde)
    if linha is None:
        dialeto = session.get_bind().dialect.name
        if dialeto not in _INSERT:
            raise RuntimeError(f"upsert da semana-padrao sem suporte no banco {dialeto}")
        session.execute(
            _INSERT[dialeto](SemanaPadrao)
            .values(atleta_id=atleta_id, vigente_desde=vigente_desde, definido_por=definido_por, definido_em=agora)
            .on_conflict_do_nothing(index_elements=["atleta_id", "vigente_desde"])
        )
        linha = _buscar(session, atleta_id, vigente_desde)
        if linha is None:  # nao foi conflito: nao deveria acontecer, nao esconde
            raise RuntimeError("vigencia da semana-padrao nao encontrada depois do INSERT")
    return linha


def reaplicar_tipos(session: Session, atleta_id: int, vigente_desde: date) -> int:
    """PONTO DE EXTENSAO da #265: reaplica o tipo das atividades do atleta com data local >= `vigente_desde`
    (ADR 0011, item 8) e devolve quantas mudaram de tipo, origem ou divergencia.

    Roda a `tipo_treino@1` por dia (`aplicar_tipos`) nas atividades com data local >= `vigente_desde`; as anteriores
    nao sao lidas nem regravadas. Nao roda `detectar_esforcos` (usa os blocos ja gravados), nao toca tipo confirmado,
    `professor` nem `trainingpeaks` e nao faz commit: dentro da transacao do PUT, se levantar, a vigencia tambem nao
    fica gravada.
    """
    return aplicar_tipos(session, atleta_id, vigente_desde)


def gravar_vigencia(
    session: Session, atleta_id: int, vigente_desde: date, definido_por: str, itens: list[ItemNovo]
) -> tuple[SemanaPadrao, int]:
    """Cria ou substitui a vigencia `vigente_desde` numa transacao so (cabecalho, itens e reaplicacao) e faz commit.
    Falhou em qualquer ponto: rollback de tudo. Devolve a linha gravada e `atividades_reaplicadas`."""
    agora = datetime.now(timezone.utc)
    try:
        linha = _criar_ou_buscar(session, atleta_id, vigente_desde, definido_por, agora)
        # atualiza o cabecalho primeiro: no Postgres isso toma o lock da linha e serializa os PUT concorrentes
        # antes de apagar e regravar os itens.
        linha.definido_por, linha.definido_em = definido_por, agora
        session.flush()
        for antigo in list(linha.itens):
            session.delete(antigo)
        session.flush()
        session.expire(linha, ["itens"])
        for i in itens:
            session.add(SemanaPadraoItem(
                semana_padrao_id=linha.id, dia_semana=i.dia_semana, modalidade=i.modalidade, tipo_treino=i.tipo_treino))
        session.flush()
        reaplicadas = reaplicar_tipos(session, atleta_id, vigente_desde)
        session.commit()
    except BaseException:
        session.rollback()
        raise
    session.refresh(linha)
    return linha, reaplicadas
