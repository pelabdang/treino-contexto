"""Perguntas prontas do chat, escolhidas pelo que o atleta tem (adendo 17 da ADR 0004).

Os textos ficam FIXOS aqui (nada vem do modelo nem de dado do atleta). A escolha olha so contagens do atleta (treinos das ultimas 8 semanas,
check-ins, carga, noites importadas) e a ordem e estavel: a do catalogo, sem aleatorio; saem as 6 primeiras cujo requisito vale.
Cada frase foi escrita para caber numa ferramenta do chat (a coluna `ferramentas`); o teste confere isso contra o registro. Nao le texto de
check-in, nao grava nada e nao chama o provedor.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, CargaAtividade, CheckinTreino, RecuperacaoDia
from app.servicos.fuso import inicio_local

VERSAO = "perguntas_prontas@1"
MAXIMO = 6
JANELA_DIAS = 56  # 8 semanas
JANELA_RECUPERACAO_DIAS = 7


@dataclass(frozen=True)
class Contexto:
    hoje: date
    treinos: list[tuple[date, str, str | None]]  # (dia local, modalidade, tipo_treino) das ultimas 8 semanas
    checkins: list[date]  # dia local do treino de cada check-in dos ultimos 28 dias
    com_carga: int  # treinos das ultimas 8 semanas com carga calculada
    noites_recentes: int  # noites importadas nos ultimos 7 dias

    def n(self, modalidade: str | None = None, tipo: str | None = None, dias: int = JANELA_DIAS) -> int:
        corte = self.hoje - timedelta(days=dias - 1)
        return sum(1 for d, m, t in self.treinos if d >= corte and (modalidade is None or m == modalidade) and (tipo is None or t == tipo))


@dataclass(frozen=True)
class Pergunta:
    id: str
    texto: str
    ferramentas: tuple[str, ...]  # as ferramentas que respondem a frase
    vale: Callable[[Contexto], bool]


CATALOGO: tuple[Pergunta, ...] = (
    Pergunta("ultimo_treino", "Como foi o meu último treino?", ("listar_atividades", "ver_atividade"), lambda c: c.n() >= 1),
    Pergunta("semana_vs_passada", "Como foi esta semana comparada com a passada?", ("comparar_periodos",), lambda c: c.n(dias=14) >= 2),
    Pergunta("pace_leve", "Meu pace nos treinos leves melhorou no último mês?", ("comparar_periodos",), lambda c: c.n("corrida", "leve") >= 3),
    Pergunta("forma_hoje", "Como está a minha forma hoje?", ("ler_carga_forma",), lambda c: c.com_carga >= 1),
    Pergunta("tiros", "Meus tiros estão ficando mais rápidos?", ("ler_serie",), lambda c: c.n("corrida", "intervalado") >= 2),
    Pergunta("checkin_ontem", "Como foi o check-in de ontem?", ("listar_checkins",), lambda c: (c.hoje - timedelta(days=1)) in c.checkins),
    Pergunta("sono", "Como foi o meu sono na última noite?", ("ler_recuperacao",), lambda c: c.noites_recentes >= 1),
    Pergunta("natacao", "Como está o meu ritmo na natação?", ("ler_serie",), lambda c: c.n("natacao") >= 3),
    Pergunta("ciclismo", "Como foi o meu último treino de ciclismo?", ("listar_atividades", "ver_atividade"), lambda c: c.n("ciclismo") >= 1),
    Pergunta("mais_longo", "Qual foi o meu treino mais longo este ano?", ("listar_atividades",), lambda c: c.n() >= 1),
    Pergunta("pior_sensacao", "Quando eu me senti pior nos treinos?", ("listar_checkins",), lambda c: len(c.checkins) >= 3),
)


def _dia_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def contexto_do_atleta(session: Session, atleta_id: int, hoje: date) -> Contexto:
    corte = hoje - timedelta(days=JANELA_DIAS)  # um dia de folga; o dia local exato e conferido em Python
    ativs = session.execute(select(Atividade.id, Atividade.inicio, Atividade.fuso_min, Atividade.modalidade, Atividade.tipo_treino)
                            .where(Atividade.atleta_id == atleta_id, Atividade.inicio >= _dia_utc(corte))).all()
    treinos, dia_de = [], {}
    for aid, inicio, fuso, modalidade, tipo in ativs:
        dia = inicio_local(inicio, fuso).date()
        dia_de[aid] = dia
        if dia > hoje - timedelta(days=JANELA_DIAS) and dia <= hoje:
            treinos.append((dia, modalidade, tipo))
    ids_checkin = session.scalars(select(CheckinTreino.atividade_id).where(CheckinTreino.atividade_id.in_(list(dia_de)))).all() if dia_de else []
    checkins = [dia_de[i] for i in ids_checkin if dia_de[i] > hoje - timedelta(days=28)]
    com_carga = (session.scalar(select(CargaAtividade.id).where(CargaAtividade.atividade_id.in_(list(dia_de)), CargaAtividade.estado == "calculada").limit(1))
                 is not None) if dia_de else False
    noites = session.scalars(select(RecuperacaoDia.noite).where(RecuperacaoDia.atleta_id == atleta_id,
                                                                RecuperacaoDia.noite > hoje - timedelta(days=JANELA_RECUPERACAO_DIAS))).all()
    return Contexto(hoje, treinos, checkins, 1 if com_carga else 0, len(noites))


def perguntas_prontas(session: Session, atleta_id: int, hoje: date) -> list[Pergunta]:
    """Ate 6 perguntas, na ordem do catalogo, so as que o atleta tem como responder."""
    ctx = contexto_do_atleta(session, atleta_id, hoje)
    return [p for p in CATALOGO if p.vale(ctx)][:MAXIMO]
