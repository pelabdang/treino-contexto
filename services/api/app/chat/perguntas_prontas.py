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

VERSAO = "perguntas_prontas@2"
MAXIMO = 6
MINIMO_NA_LISTA = 3  # o Inicio mostra as 3 primeiras: atleta sem dado recebe a lista de apoio, nunca uma lista vazia
JANELA_DIAS = 84  # 12 semanas: a maior janela das regras (natacao, sentir-se mal)
JANELA_RECUPERACAO_DIAS = 7
COMPARACAO_DIAS = 28  # os rolantes de `comparar_periodos` terminam ONTEM: conta-se de ontem para tras


@dataclass(frozen=True)
class Contexto:
    hoje: date
    treinos: list[tuple[date, str, str | None]]  # (dia local, modalidade, tipo_treino) das ultimas 12 semanas
    checkins: list[date]  # dia local do treino de cada check-in dos ultimos 28 dias
    maus_checkins: int  # check-ins com sensacao "mal" ou "muito mal" nas ultimas 12 semanas
    com_carga: int  # treinos das ultimas 8 semanas com carga calculada
    noites_recentes: int  # noites importadas nos ultimos 7 dias

    def n(self, modalidade: str | None = None, tipo: str | None = None, dias: int = 56) -> int:
        """Treinos nos `dias` ate hoje (inclusive)."""
        return self.entre(0, dias - 1, modalidade, tipo)

    def entre(self, mais_novo: int, mais_velho: int, modalidade: str | None = None, tipo: str | None = None) -> int:
        """Treinos de `hoje - mais_velho` a `hoje - mais_novo` (0 = hoje, 1 = ontem)."""
        de, ate = self.hoje - timedelta(days=mais_velho), self.hoje - timedelta(days=mais_novo)
        return sum(1 for d, m, t in self.treinos if de <= d <= ate and (modalidade is None or m == modalidade) and (tipo is None or t == tipo))

    def nos_dois_periodos(self, minimo: int, modalidade: str, tipo: str | None = None, dias: int = COMPARACAO_DIAS) -> bool:
        """`minimo` treinos na janela rolante de `dias` que termina ontem E na anterior (a conta que `comparar_periodos` exige)."""
        return self.entre(1, dias, modalidade, tipo) >= minimo and self.entre(dias + 1, 2 * dias, modalidade, tipo) >= minimo


@dataclass(frozen=True)
class Pergunta:
    id: str
    texto: str
    dica: tuple[tuple[str, dict], ...]  # (ferramenta, argumentos) que respondem a frase; `INICIO_DO_ANO` e `HOJE` valem as datas do dia
    vale: Callable[[Contexto], bool]

    @property
    def ferramentas(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(f for f, _ in self.dica))


CATALOGO: tuple[Pergunta, ...] = (
    Pergunta("ultimo_treino", "Como foi o meu último treino?",
             (("listar_atividades", {"ordem": "recentes", "limite": 1}), ("ver_atividade", {"atividade_id": 1})), lambda c: c.n() >= 1),
    Pergunta("sete_dias", "Como foram os meus últimos 7 dias comparados com os 7 anteriores?",
             (("comparar_periodos", {"serie_id": "corrida.volume_km", "periodo_a": "ultimos_7_dias", "periodo_b": "ultimos_7_dias_anteriores"}),),
             lambda c: c.entre(1, 7, "corrida") >= 1 and c.entre(8, 14, "corrida") >= 1),
    Pergunta("pace_leve", "Meu pace nos treinos leves ficou mais rápido no último mês?",
             (("comparar_periodos", {"serie_id": "corrida.pace.leve", "periodo_a": "ultimos_28_dias", "periodo_b": "ultimos_28_dias_anteriores"}),),
             lambda c: c.nos_dois_periodos(3, "corrida", "leve")),
    Pergunta("forma_hoje", "Como está a minha forma hoje?", (("ler_carga_forma", {}),), lambda c: c.com_carga >= 1),
    Pergunta("tiros", "Meus tiros ficaram mais rápidos no último mês?",
             (("comparar_periodos", {"serie_id": "corrida.tiros", "periodo_a": "ultimos_28_dias", "periodo_b": "ultimos_28_dias_anteriores"}),),
             lambda c: c.nos_dois_periodos(2, "corrida", "intervalado")),
    Pergunta("checkin_ontem", "Como foi o check-in de ontem?", (("listar_checkins", {"de": "ONTEM", "ate": "ONTEM"}),),
             lambda c: (c.hoje - timedelta(days=1)) in c.checkins),
    Pergunta("sono", "Como foi o meu sono na última noite?", (("ler_recuperacao", {"periodo": "ultimos_7_dias"}),), lambda c: c.noites_recentes >= 1),
    Pergunta("natacao", "Como está o meu ritmo na natação?", (("ler_serie", {"serie_id": "natacao.ritmo", "periodo": "ultimas_12_semanas"}),),
             lambda c: c.n("natacao", dias=84) >= 3),
    Pergunta("ciclismo", "Como foi o meu último treino de ciclismo?",
             (("listar_atividades", {"modalidade": "ciclismo", "ordem": "recentes", "limite": 1}), ("ver_atividade", {"atividade_id": 1})),
             lambda c: c.n("ciclismo") >= 1),
    # `ultimo_ano` sao 365 dias, nao o ano de calendario: "este ano" pede `de` = 01/01 e `ate` = hoje
    Pergunta("mais_longo", "Qual foi o meu treino de corrida mais longo este ano?",
             (("listar_atividades", {"modalidade": "corrida", "ordem": "maiores", "limite": 1, "de": "INICIO_DO_ANO", "ate": "HOJE"}),),
             lambda c: c.n("corrida", dias=84) >= 1),
    Pergunta("treinos_mal", "Em quais treinos eu me senti mal?", (("listar_checkins", {"periodo": "ultimas_12_semanas"}),), lambda c: c.maus_checkins >= 1),
)
# Para quem ainda nao tem dado para nenhuma das de cima (a ferramenta responde com `sem_dados` e o motivo), nunca menos de 3 frases.
APOIO: tuple[Pergunta, ...] = (
    Pergunta("apoio_ultimos", "Quais foram os meus últimos treinos?", (("listar_atividades", {"ordem": "recentes", "limite": 5}),), lambda c: True),
    Pergunta("apoio_ultimo", "Como foi o meu último treino?",
             (("listar_atividades", {"ordem": "recentes", "limite": 1}), ("ver_atividade", {"atividade_id": 1})), lambda c: True),
    Pergunta("apoio_forma", "Como está a minha forma hoje?", (("ler_carga_forma", {}),), lambda c: True),
    Pergunta("apoio_checkins", "Como foram os meus check-ins nas últimas semanas?", (("listar_checkins", {"periodo": "ultimas_12_semanas"}),), lambda c: True),
)


def _dia_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def contexto_do_atleta(session: Session, atleta_id: int, hoje: date) -> Contexto:
    corte = hoje - timedelta(days=JANELA_DIAS + 1)  # um dia de folga; o dia local exato e conferido em Python
    ativs = session.execute(select(Atividade.id, Atividade.inicio, Atividade.fuso_min, Atividade.modalidade, Atividade.tipo_treino)
                            .where(Atividade.atleta_id == atleta_id, Atividade.inicio >= _dia_utc(corte))).all()
    treinos, dia_de = [], {}
    for aid, inicio, fuso, modalidade, tipo in ativs:
        dia = inicio_local(inicio, fuso).date()
        dia_de[aid] = dia
        if hoje - timedelta(days=JANELA_DIAS) < dia <= hoje:
            treinos.append((dia, modalidade, tipo))
    ids = list(dia_de)
    checkins, maus = [], 0
    if ids:
        for aid, sensacao in session.execute(select(CheckinTreino.atividade_id, CheckinTreino.sensacao).where(CheckinTreino.atividade_id.in_(ids))).all():
            if dia_de[aid] > hoje - timedelta(days=28):
                checkins.append(dia_de[aid])
            if sensacao <= 2:
                maus += 1
    com_carga = ids and session.scalar(select(CargaAtividade.id).where(CargaAtividade.atividade_id.in_(ids), CargaAtividade.estado == "calculada").limit(1)) is not None
    noites = session.scalars(select(RecuperacaoDia.noite).where(RecuperacaoDia.atleta_id == atleta_id,
                                                                RecuperacaoDia.noite > hoje - timedelta(days=JANELA_RECUPERACAO_DIAS))).all()
    return Contexto(hoje, treinos, checkins, maus, 1 if com_carga else 0, len(noites))


def perguntas_prontas(session: Session, atleta_id: int, hoje: date) -> list[Pergunta]:
    """De 3 a 6 perguntas, na ordem do catalogo: as que o atleta tem como responder e, se forem menos de 3, as de apoio (sem repetir frase)."""
    ctx = contexto_do_atleta(session, atleta_id, hoje)
    escolhidas = [p for p in CATALOGO if p.vale(ctx)][:MAXIMO]
    for p in APOIO:
        if len(escolhidas) >= MINIMO_NA_LISTA:
            break
        if p.texto not in {e.texto for e in escolhidas}:
            escolhidas.append(p)
    return escolhidas
