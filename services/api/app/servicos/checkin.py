"""Check-in pos-treino: prazo, elegibilidade e gravacao (issue #296, ADR 0012, itens 3 a 5).

Dado pessoal e de saude (a observacao e o mais sensivel): nenhum valor do check-in vai para log, para excecao ou para saida de
comando; so ids e contagens. O que muda de decisao de produto (prazo e quais treinos pedem check-in) fica em constantes aqui,
aguardando o "A confirmar" 1 e 2 do Angelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as _insert_pg
from sqlalchemy.dialects.sqlite import insert as _insert_sqlite
from sqlalchemy.orm import Session

from app.db.models import CHECKIN_ATALHOS, CHECKIN_VERSAO, Atividade, CheckinTreino
from app.servicos.fuso import FUSO_PADRAO, data_local

# --- Parametros de produto, faceis de mudar (ADR 0012, "A confirmar" 1 e 2) -------------------------------------------
PRAZO_DIAS = 7  # criar o check-in ate 7 dias depois do dia do treino; editar e apagar nao tem prazo
SUBTIPOS_SEM_CHECKIN = frozenset({"multiesporte_pai", "troca"})  # o pai repete as partes e a troca nao e treino
# -----------------------------------------------------------------------------------------------------------------------

_INSERT = {"postgresql": _insert_pg, "sqlite": _insert_sqlite}

PSE_ANCORA = {0: "repouso", 1: "muito leve", 2: "leve", 3: "moderado", 4: "um pouco difícil", 5: "difícil",
              7: "muito difícil", 10: "máximo"}  # 6, 8 e 9 ficam so com o numero (ADR 0012, item 2)
SENSACAO_TEXTO = {1: "muito mal", 2: "mal", 3: "normal", 4: "bem", 5: "muito bem"}
ATALHO_TEXTO = {"dor": "Dor", "cansaco": "Cansaço", "sono_ruim": "Sono ruim", "calor": "Calor",
                "trabalho_estresse": "Trabalho ou estresse"}
assert tuple(ATALHO_TEXTO) == CHECKIN_ATALHOS


@dataclass(frozen=True)
class DadosCheckin:
    pse: int
    sensacao: int
    nada_a_relatar: bool
    atalhos: tuple[str, ...]
    texto: str | None  # ja aparado; vazio vira None


def hoje_local() -> date:
    """Hoje no calendario de `America/Sao_Paulo` (relogio injetavel nos testes)."""
    return datetime.now(FUSO_PADRAO).date()


def dias_ate_hoje(dia: date, hoje: date, dias: int) -> bool:
    """A janela `[hoje - dias, hoje]` da ADR 0012 (item 3): `data_local >= hoje - dias`. Uma funcao so, usada pela criacao
    (`PRAZO_DIAS`) e, na #298, pela lista de pendentes."""
    return dia >= hoje - timedelta(days=dias)


def elegivel(a: Atividade) -> bool:
    return a.subtipo not in SUBTIPOS_SEM_CHECKIN


def no_prazo(a: Atividade, hoje: date | None = None) -> bool:
    return dias_ate_hoje(data_local(a.inicio, a.fuso_min), hoje or hoje_local(), PRAZO_DIAS)


def _buscar(session: Session, atividade_id: int) -> CheckinTreino | None:
    return session.scalars(select(CheckinTreino).where(CheckinTreino.atividade_id == atividade_id)).first()


def checkin_da_atividade(session: Session, atividade_id: int) -> CheckinTreino | None:
    return _buscar(session, atividade_id)


def gravar_checkin(session: Session, a: Atividade, d: DadosCheckin) -> CheckinTreino:
    """Cria ou substitui o check-in da atividade (um por atividade) e faz commit.

    Busca a linha; se nao ha, `INSERT ... ON CONFLICT DO NOTHING` em `atividade_id` (por dialeto), nova busca (acha a
    linha de um `PUT` simultaneo) e `UPDATE` de tudo, menos `id` e `registrado_em`. Sem savepoint: o `SAVEPOINT` do pysqlite
    commita a transacao externa no `RELEASE` (mesma decisao do upsert da semana-padrao, ADR 0011).
    """
    agora = datetime.now(timezone.utc)
    campos = {c: c in d.atalhos for c in CHECKIN_ATALHOS}
    linha = _buscar(session, a.id)
    if linha is None:
        dialeto = session.get_bind().dialect.name
        if dialeto not in _INSERT:
            raise RuntimeError(f"upsert do check-in sem suporte no banco {dialeto}")
        session.execute(
            _INSERT[dialeto](CheckinTreino)
            .values(atividade_id=a.id, pse=d.pse, sensacao=d.sensacao, nada_a_relatar=d.nada_a_relatar, texto=d.texto,
                    versao=CHECKIN_VERSAO, registrado_em=agora, atualizado_em=agora, **campos)
            .on_conflict_do_nothing(index_elements=["atividade_id"])
        )
        linha = _buscar(session, a.id)
        if linha is None:
            raise RuntimeError("check-in nao encontrado depois do INSERT")
    linha.pse, linha.sensacao, linha.nada_a_relatar, linha.texto = d.pse, d.sensacao, d.nada_a_relatar, d.texto
    for c, v in campos.items():
        setattr(linha, c, v)
    linha.versao, linha.atualizado_em = CHECKIN_VERSAO, agora
    session.commit()
    session.refresh(linha)
    return linha


def apagar_checkin(session: Session, atividade_id: int) -> bool:
    """Remove a linha (nao so limpa campos). Idempotente: devolve se havia."""
    linha = _buscar(session, atividade_id)
    if linha is None:
        return False
    session.delete(linha)
    session.commit()
    return True


def apagar_checkins_do_atleta(session: Session, atleta_id: int) -> int:
    """Apaga todos os check-ins das atividades do atleta (LGPD). O atleta e as atividades ficam. Devolve so a contagem."""
    n = session.execute(
        delete(CheckinTreino)
        .where(CheckinTreino.atividade_id.in_(select(Atividade.id).where(Atividade.atleta_id == atleta_id)))
        .execution_options(synchronize_session=False)
    ).rowcount
    session.commit()
    return n
