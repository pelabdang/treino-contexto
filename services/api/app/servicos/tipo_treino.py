"""Grava o tipo de treino das atividades pela `tipo_treino@1` (issue #265, ADR 0011, itens 2 a 5 e 8).

Liga a função pura `app.metricas.tipo_treino.classificar` ao banco: lê as atividades do atleta, a semana-padrão
(vigências e itens) e os blocos já gravados (ADR 0008), e grava `tipo_treino`, `tipo_origem`, `tipo_versao` e
`tipo_divergencia` **só nas linhas que mudam**. Nunca toca tipo confirmado, `professor` nem `trainingpeaks`. Não roda
`detectar_esforcos` (quem quer os blocos novos chama `classificar_atividades`). Não faz commit: o chamador decide
(o `PUT` da semana-padrão faz rollback de tudo se algo falhar).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade, SemanaPadrao
from app.metricas import tipo_treino as tt
from app.metricas.tiros_1km import BlocoEntrada, tiros_de_blocos
from app.servicos.fuso import data_local


def _bloco(b) -> BlocoEntrada:
    return BlocoEntrada(
        ordem=b.ordem, categoria=b.categoria, volta_inicial=b.volta_inicial, volta_final=b.volta_final,
        distancia_m=b.distancia_m, duracao_s=b.duracao_s, fc_media=b.fc_media, faixa=b.faixa,
        parada_apos_s=b.parada_apos_s,
    )  # fmt: skip


def _utc(dt: datetime) -> datetime:
    """O SQLite devolve `inicio` sem fuso (UTC) e a sessão pode ter o mesmo campo com fuso: compara-se só em UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def estrutura_dos_blocos(a: Atividade) -> tuple[str | None, int]:
    """Resume os blocos gravados da corrida: (`estrutura`, `n_tiros`). Sem blocos (ou outra modalidade): `(None, 0)`."""
    if a.modalidade != "corrida" or not a.blocos:
        return None, 0
    blocos = [_bloco(b) for b in a.blocos]
    r = tiros_de_blocos(blocos, a.modalidade)
    if r.eh_intervalado:
        return tt.TIROS, len(r.tiros)
    if all(b.categoria == "leve" for b in blocos):
        return tt.SEM_ESFORCO, 0
    return tt.ESFORCO, 0


def vigencias_do_atleta(session: Session, atleta_id: int) -> list[tt.Vigencia]:
    linhas = session.scalars(
        select(SemanaPadrao).where(SemanaPadrao.atleta_id == atleta_id).options(selectinload(SemanaPadrao.itens))
    ).all()
    return [
        tt.Vigencia(s.vigente_desde, tuple(tt.Item(i.dia_semana, i.modalidade, i.tipo_treino) for i in s.itens))
        for s in linhas
    ]


def aplicar_tipos(session: Session, atleta_id: int, desde: date | None = None) -> int:
    """Roda a `tipo_treino@1` nas atividades do atleta com data local >= `desde` (todas, sem `desde`) e grava o que mudou.

    A função pura decide por dia (o item vale para uma atividade por modalidade e dia), então cortar por data local
    não muda o resultado do dia. Devolve quantas atividades mudaram de tipo, origem, versão ou divergência.
    """
    consulta = (
        select(Atividade).where(Atividade.atleta_id == atleta_id).options(selectinload(Atividade.blocos))
    )
    if desde is not None:  # folga de um dia para o fuso; a data local exata é conferida abaixo
        corte = desde - timedelta(days=1)
        consulta = consulta.where(Atividade.inicio >= datetime(corte.year, corte.month, corte.day, tzinfo=timezone.utc))
    linhas = []
    for a in session.scalars(consulta).all():
        dia = data_local(a.inicio, a.fuso_min)
        if desde is None or dia >= desde:
            linhas.append((a, dia))

    entradas = []
    for a, dia in linhas:
        estrutura, n = estrutura_dos_blocos(a)
        entradas.append(tt.Atividade(
            id=a.id, dia=dia, modalidade=a.modalidade, inicio=_utc(a.inicio), duracao_s=a.duracao_s, subtipo=a.subtipo,
            tipo_treino=a.tipo_treino, tipo_origem=a.tipo_origem, tipo_confirmado=bool(a.tipo_confirmado),
            estrutura=estrutura, n_tiros=n,
        ))
    resultado = tt.classificar(entradas, vigencias_do_atleta(session, atleta_id))

    mudaram = 0
    for a, _ in linhas:
        if a.tipo_confirmado or a.tipo_origem in tt.ORIGENS_PROTEGIDAS:
            continue  # nunca muda (nem a versao)
        r = resultado[a.id]
        novo = (r.tipo_treino, r.tipo_origem, r.versao, r.divergencia)
        if (a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia) != novo:
            a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia = novo
            mudaram += 1
    session.flush()
    return mudaram
