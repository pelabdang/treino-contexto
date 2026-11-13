"""Recuperacao no pacote de fatos: banco -> `recuperacao@1` e `importado_em` da noite do treino (issue #374, ADR 0014 itens 2 e 4).

Le o que a #372 gravou (`recuperacao_banco`), converte `NoiteGravada` em `rc.Noite` e usa a MESMA regra `rc.noite_do_treino` para
(a) montar o bloco `recuperacao` do pacote e (b) dar o "importado_em de hoje" da comparacao do "desatualizado" (ADR 0014, item 4):
madrugada, `fora_do_periodo` e sem noite valem `None`. So le; nao grava, nao registra nada (dado de saude: so no banco local).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Atividade
from app.ingestao.garmin.unidades import para_utc
from app.metricas import recuperacao as rc
from app.servicos.fuso import inicio_local
from app.servicos.recuperacao_banco import NoiteGravada, noites_do_atleta, primeira_noite


@dataclass(frozen=True)
class RecuperacaoDoAtleta:
    """As noites lidas do banco (uma leitura) e a mais antiga que o atleta tem, para `fora_do_periodo`."""

    noites: dict[date, NoiteGravada]
    primeira: date | None


def carregar_do_atleta(session: Session, atleta_id: int) -> RecuperacaoDoAtleta:
    """Todas as noites do atleta numa consulta: serve a um lote (worker) de varios treinos."""
    noites = noites_do_atleta(session, atleta_id)
    return RecuperacaoDoAtleta(noites, min(noites, default=None))


def carregar_da_atividade(session: Session, atividade: Atividade) -> RecuperacaoDoAtleta:
    """So o que um treino precisa: a janela (`D-28` a `D`) e a primeira noite do atleta (duas consultas)."""
    dia = inicio_local(atividade.inicio, atividade.fuso_min).date()
    noites = noites_do_atleta(session, atividade.atleta_id, dia - timedelta(days=rc.PADRAO.janela_noites), dia)
    return RecuperacaoDoAtleta(noites, primeira_noite(session, atividade.atleta_id))


def _noite(n: NoiteGravada) -> rc.Noite:
    return rc.Noite(n.noite, n.sono_s, n.vfc_ms, n.fc_repouso_bpm)


def recuperacao_da_atividade(dados: RecuperacaoDoAtleta, atividade: Atividade) -> rc.Recuperacao:
    local = inicio_local(atividade.inicio, atividade.fuso_min)
    return rc.recuperacao(local.date(), local.time(), [_noite(n) for n in dados.noites.values()], primeira_noite=dados.primeira)


def importado_em_de_hoje(dados: RecuperacaoDoAtleta, atividade: Atividade) -> datetime | None:
    """O `importado_em` da noite que `noite_do_treino` devolve hoje, ou `None` (madrugada, `fora_do_periodo`, sem noite)."""
    local = inicio_local(atividade.inicio, atividade.fuso_min)
    noite, _ = rc.noite_do_treino(local.date(), local.time(), [_noite(n) for n in dados.noites.values()], primeira_noite=dados.primeira)
    return None if noite is None else dados.noites[noite.noite].importado_em


def mesmo_instante(a: datetime | None, b: datetime | None) -> bool:
    """Igualdade de `importado_em` com os dois lados em UTC (o SQLite devolve sem fuso); `None` so e igual a `None`."""
    if a is None or b is None:
        return a is b
    return para_utc(a) == para_utc(b)
