"""Lista de treinos do atleta, paginada por cursor (UX: aba "Treinos" e tela inicial).

- Ordem: mais recente primeiro, por `(inicio, id)` decrescente. O cursor `antes_de` e `"<inicio UTC ISO>~<id>"` (o `proximo` da pagina anterior):
  traz so o que vem DEPOIS dele na ordem, sem pular nem repetir treino mesmo se entrar atividade nova no topo.
- Uma consulta traz a pagina inteira (`LIMIT + 1`, para saber se ha mais), com check-in, feedback e rotulo de transicao por JOIN: sem N+1.
- Item enxuto: nada de clima, esforcos, carga, linha de base, texto de check-in nem texto de feedback (dado de saude fica no `GET` da atividade).
- O estado do feedback aqui compara so o que a pagina ja tem (check-in, versao, tipo e transicao); a noite e o clima (que pedem outras consultas)
  nao entram. Pode haver "pronto" aqui e "desatualizado" no detalhe por causa da noite ou do clima.
- `checkin_pendente`: elegivel, sem check-in e dentro do prazo (a mesma regra de `checkin_aberto`). O prazo e por data local; o SQL corta com um dia
  de folga (as linhas dentro do prazo sao poucas) e a data local confere em Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Atividade, CheckinTreino
from app.ingestao.garmin.unidades import para_utc
from app.servicos import checkin as checkin_svc
from app.servicos.feedback import tipo_atual, transicao_atual
from app.servicos.feedback_leitura import feedback_da_atividade

LIMITE_PADRAO = 20
LIMITE_MAX = 100
_CURSOR = re.compile(r"^(?P<inicio>[0-9T:.+\-Z ]{10,40})~(?P<id>[0-9]{1,12})$")


class CursorInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Cursor:
    inicio: datetime
    id: int

    def texto(self) -> str:
        return f"{para_utc(self.inicio).isoformat()}~{self.id}"


def ler_cursor(texto: str) -> Cursor:
    m = _CURSOR.match(texto or "")
    if not m:
        raise CursorInvalido()
    try:
        return Cursor(para_utc(datetime.fromisoformat(m["inicio"].replace("Z", "+00:00"))), int(m["id"]))
    except ValueError:
        raise CursorInvalido() from None


@dataclass(frozen=True)
class Pagina:
    atividades: list[Atividade]
    proximo: Cursor | None


def pagina(session: Session, atleta_id: int, limite: int = LIMITE_PADRAO, antes_de: Cursor | None = None, modalidade: str | None = None,
           checkin_pendente: bool = False, hoje: date | None = None) -> Pagina:
    limite = max(1, min(limite, LIMITE_MAX))
    q = (
        select(Atividade)
        .where(Atividade.atleta_id == atleta_id)
        .options(joinedload(Atividade.checkin).joinedload(CheckinTreino.feedback), joinedload(Atividade.rotulo_transicao))
        .order_by(Atividade.inicio.desc(), Atividade.id.desc())
    )
    if modalidade:
        q = q.where(Atividade.modalidade == modalidade)
    if antes_de is not None:
        q = q.where(or_(Atividade.inicio < antes_de.inicio, and_(Atividade.inicio == antes_de.inicio, Atividade.id < antes_de.id)))
    if checkin_pendente:
        hoje = hoje or checkin_svc.hoje_local()
        corte = hoje - timedelta(days=checkin_svc.PRAZO_DIAS + 1)
        q = q.where(~Atividade.checkin.has(), Atividade.inicio >= datetime(corte.year, corte.month, corte.day, tzinfo=timezone.utc))
        linhas = [a for a in session.scalars(q).unique() if checkin_estado(a, hoje) == "pendente"][: limite + 1]
    else:
        linhas = list(session.scalars(q.limit(limite + 1)).unique())
    tem_mais = len(linhas) > limite
    linhas = linhas[:limite]
    return Pagina(linhas, Cursor(linhas[-1].inicio, linhas[-1].id) if tem_mais and linhas else None)


def checkin_estado(a: Atividade, hoje: date | None = None) -> str:
    """`feito`; `pendente` (sem check-in e no prazo); `vencido` (sem check-in e fora do prazo); `nao_se_aplica` (multiesporte_pai e troca)."""
    if not checkin_svc.elegivel(a):
        return "nao_se_aplica"
    if a.checkin is not None:
        return "feito"
    return "pendente" if checkin_svc.no_prazo(a, hoje) else "vencido"


def feedback_estado(a: Atividade, hoje: date | None = None) -> str | None:
    """O estado do cartao de feedback sem o texto. `None` em multiesporte_pai e troca."""
    aberto = checkin_svc.checkin_aberto(a, a.checkin is not None, hoje)
    f = feedback_da_atividade(a, a.checkin, aberto, tipo_hoje=tipo_atual(a), transicao_hoje=transicao_atual(a))
    return None if f is None else f.estado
