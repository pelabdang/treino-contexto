"""Confirmacao e correcao do tipo do treino pelo professor, em lote (issue #425, ADR 0015, item 5).

Tudo ou nada: valida o lote inteiro antes de gravar e so entao grava; quem chama faz um `commit` (ou `rollback`).
Ordem das recusas: (2) atividade inexistente OU fora do filtro de vinculo e consentimento -> `AtividadeNaoEncontrada` (um so tipo,
sem dizer quais ids), (3) so entao `AtividadeSemTipo` (multiesporte, ou sem tipo para confirmar), para ele nao revelar que a
atividade existe. A validacao de forma (tipo fora dos cinco, vazio, repetido, mais de 200) e da rota, antes do banco.
Nao guarda nem loga tipo, nome ou texto: so contagens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade
from app.servicos.checkin import elegivel
from app.servicos.professor import so_atletas_visiveis

LOTE_MAX = 200


class AtividadeNaoEncontrada(Exception):
    """Alguma atividade do lote nao existe ou e de atleta fora do filtro. Sem ids na mensagem."""


class AtividadeSemTipo(Exception):
    """Alguma atividade do lote e multiesporte/troca, ou nao tem tipo para confirmar."""


@dataclass(frozen=True)
class ItemLote:
    atividade_id: int
    tipo_treino: str | None = None  # None: confirmar o tipo que a atividade ja tem


@dataclass(frozen=True)
class ResultadoLote:
    confirmados: int
    corrigidos: int


def confirmar_ou_corrigir(session: Session, professor_id: int, itens: list[ItemLote], agora: datetime) -> ResultadoLote:
    """Aplica o lote (nao faz commit). `professor_id` e o da configuracao. Levanta antes de gravar qualquer coisa."""
    ids = [i.atividade_id for i in itens]
    atividades = {
        a.id: a for a in session.scalars(
            so_atletas_visiveis(select(Atividade).where(Atividade.id.in_(ids)), Atividade.atleta_id, professor_id, agora))
    }
    if len(atividades) != len(set(ids)):
        raise AtividadeNaoEncontrada
    alvos: list[tuple[Atividade, str]] = []
    for item in itens:
        a = atividades[item.atividade_id]
        alvo = item.tipo_treino or a.tipo_treino
        if not elegivel(a) or alvo is None:
            raise AtividadeSemTipo
        alvos.append((a, alvo))

    confirmados = corrigidos = 0
    for a, alvo in alvos:
        if alvo == a.tipo_treino:  # confirmar sem mudar: so marca (origem, versao e divergencia ficam)
            confirmados += 1
            if not a.tipo_confirmado:
                a.tipo_confirmado, a.tipo_confirmado_por, a.tipo_confirmado_em = True, professor_id, agora
        else:  # corrigir: tudo na mesma gravacao (o CHECK exige divergencia nula com origem `professor`)
            corrigidos += 1
            a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia = alvo, "professor", None, None
            a.tipo_confirmado, a.tipo_confirmado_por, a.tipo_confirmado_em = True, professor_id, agora
    session.flush()
    return ResultadoLote(confirmados, corrigidos)
