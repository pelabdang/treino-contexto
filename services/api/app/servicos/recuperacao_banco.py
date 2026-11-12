"""Leitura em lote e gravacao da recuperacao diaria (ADR 0014, itens 1 e 5; issue #372).

`recuperacao_dia` e dado de saude: so no banco local, nunca em log nem em mensagem de erro, sem rota que o devolva.
Esta camada so le e grava; quem calcula o "normal" e a funcao pura `recuperacao@1` (#373) e quem monta o pacote e
`fatos_treino@2` (#374), que usam `noites_do_atleta` e `primeira_noite`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import FeedbackTreino, RecuperacaoDia

ORIGEM = "garmin_connect"


@dataclass(frozen=True)
class NoiteGravada:
    """Uma noite como esta no banco. `importado_em` so muda quando algum dos tres valores muda."""

    noite: date  # data local de ACORDAR
    sono_s: int | None
    vfc_ms: float | None
    fc_repouso_bpm: int | None
    importado_em: datetime


def noites_do_atleta(session: Session, atleta_id: int, desde: date | None = None, ate: date | None = None,
                     origem: str = ORIGEM) -> dict[date, NoiteGravada]:
    """As noites do atleta entre `desde` e `ate` (inclusive; sem limite se omitidos), por data, em UMA consulta.

    E a leitura em lote para o pacote de fatos e para o "normal" (as 28 noites `D-28` a `D-1`): a ausencia da chave e o
    "sem dado" (noite sem nenhuma medida nao vira linha).
    """
    q = select(RecuperacaoDia).where(RecuperacaoDia.atleta_id == atleta_id, RecuperacaoDia.origem == origem)
    if desde is not None:
        q = q.where(RecuperacaoDia.noite >= desde)
    if ate is not None:
        q = q.where(RecuperacaoDia.noite <= ate)
    return {r.noite: NoiteGravada(r.noite, r.sono_s, r.vfc_ms, r.fc_repouso_bpm, r.importado_em)
            for r in session.scalars(q.order_by(RecuperacaoDia.noite))}


def primeira_noite(session: Session, atleta_id: int, origem: str = ORIGEM) -> date | None:
    """A noite mais antiga gravada (para `fora_do_periodo`), ou `None` se o atleta nao tem nenhuma."""
    return session.scalar(select(func.min(RecuperacaoDia.noite)).where(
        RecuperacaoDia.atleta_id == atleta_id, RecuperacaoDia.origem == origem))


def ultima_noite(session: Session, atleta_id: int, origem: str = ORIGEM) -> date | None:
    return session.scalar(select(func.max(RecuperacaoDia.noite)).where(
        RecuperacaoDia.atleta_id == atleta_id, RecuperacaoDia.origem == origem))


def gravar_noite(session: Session, atleta_id: int, noite: date, sono_s: int | None, vfc_ms: float | None,
                 fc_repouso_bpm: int | None, versao_leitura: str, agora: datetime, origem: str = ORIGEM) -> str | None:
    """*Upsert* por `(atleta_id, origem, noite)`. Devolve `nova`, `atualizada`, `igual` ou `None` (nada a gravar).

    Um valor `None` NUNCA apaga o que ja esta guardado; um valor diferente substitui e muda `importado_em`; com os tres
    iguais nada muda (nem `importado_em`, nem `versao_leitura`). Noite sem nenhuma medida e sem linha antiga nao vira linha.
    Nao faz `commit`.
    """
    atual = session.scalars(select(RecuperacaoDia).where(
        RecuperacaoDia.atleta_id == atleta_id, RecuperacaoDia.origem == origem, RecuperacaoDia.noite == noite)).first()
    if atual is None:
        if sono_s is None and vfc_ms is None and fc_repouso_bpm is None:
            return None
        session.add(RecuperacaoDia(atleta_id=atleta_id, origem=origem, noite=noite, sono_s=sono_s, vfc_ms=vfc_ms,
                                   fc_repouso_bpm=fc_repouso_bpm, versao_leitura=versao_leitura, importado_em=agora))
        session.flush()
        return "nova"
    mudou = False
    for campo, novo in (("sono_s", sono_s), ("vfc_ms", vfc_ms), ("fc_repouso_bpm", fc_repouso_bpm)):
        if novo is not None and getattr(atual, campo) != novo:
            setattr(atual, campo, novo)
            mudou = True
    if not mudou:
        return "igual"
    atual.versao_leitura = versao_leitura
    atual.importado_em = agora
    session.flush()
    return "atualizada"


def apagar_recuperacao_do_atleta(session: Session, atleta_id: int) -> tuple[int, int]:
    """Apaga as noites do atleta E os feedbacks dele com `recuperacao_importada_em IS NOT NULL` (LGPD, ADR 0014).

    O `texto` de um feedback gerado com a recuperacao contem os valores da noite; por isso ele sai junto. Feedbacks com
    `recuperacao_importada_em IS NULL` (pacote sem noite) ficam. Atleta, atividades e check-ins ficam. Devolve so as
    contagens `(noites, feedbacks)`. Idempotente. Faz `commit`.
    """
    from app.db.models import Atividade, CheckinTreino

    checkins = select(CheckinTreino.id).where(
        CheckinTreino.atividade_id.in_(select(Atividade.id).where(Atividade.atleta_id == atleta_id)))
    feedbacks = session.execute(
        delete(FeedbackTreino).where(FeedbackTreino.checkin_id.in_(checkins),
                                     FeedbackTreino.recuperacao_importada_em.is_not(None))
        .execution_options(synchronize_session=False)).rowcount
    noites = session.execute(
        delete(RecuperacaoDia).where(RecuperacaoDia.atleta_id == atleta_id)
        .execution_options(synchronize_session=False)).rowcount
    session.commit()
    return noites, feedbacks
