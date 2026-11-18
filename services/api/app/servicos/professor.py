"""Professor do piloto local e o filtro de vinculo e consentimento (ADR 0015, itens 2 e 3; issue #423).

Duas pecas, usadas por TODA rota do professor (a Meta 11 nao tem rota de professor que leia atleta fora daqui):

- `professor_da_rota`: dependencia que devolve o professor da SESSAO (`professor_da_sessao`, ADR 0016, item 5; desde a #500 nao ha
  mais `PROFESSOR_ID`). Qualquer id do caminho que nao seja o da sessao da o MESMO `404`, byte a byte, e o log nao diz o motivo:
  a resposta nao confirma que um id existe. Devolve o id da SESSAO, nunca o do caminho.
- `atletas_do_professor(professor_id, agora)`: expressao SQL (subconsulta de `atleta_id`) com o vinculo E o consentimento
  (`consentimento_em` nao nulo e `<= agora`). Entra como condicao da consulta, nunca como filtro depois de ler.

Dado de saude: nada de nome, tipo, PSE ou texto de atleta em log; o log leva so ids e contagens.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.autenticacao import PROFESSOR_INEXISTENTE, professor_da_sessao
from app.db.models import Atleta, Professor, VinculoProfessorAtleta
from app.db.session import get_session

# Corpo unico do 404 do professor: a mesma forma e os mesmos bytes para qualquer id que nao seja o da sessao (ADR 0015, item 2).
ATLETA_NAO_ENCONTRADO = {
    "detail": [{"loc": ["path", "atleta_id"], "msg": "atleta não encontrado", "type": "atleta_nao_encontrado"}]
}


def agora_utc() -> datetime:
    """O instante da requisicao (UTC com fuso). Dependencia, para o teste fixar a hora; um so por requisicao."""
    return datetime.now(timezone.utc)


def atletas_do_professor(professor_id: int, agora: datetime):
    """Subconsulta com os `atleta_id` visiveis ao professor: vinculo com consentimento dado ate `agora`.

    `agora` precisa ter fuso (nunca `now()` no SQL). Sem atalho por `assessoria_id`.
    """
    if agora.tzinfo is None:
        raise ValueError("agora precisa ter fuso (UTC)")
    return (
        select(VinculoProfessorAtleta.atleta_id)
        .where(
            VinculoProfessorAtleta.professor_id == professor_id,
            VinculoProfessorAtleta.consentimento_em.is_not(None),
            VinculoProfessorAtleta.consentimento_em <= agora,
        )
        .scalar_subquery()
    )


def professor_da_rota(professor_id: int = Depends(professor_da_sessao)) -> int:
    """Dependencia das rotas `/professores/{professor_id}/...`: o professor da SESSAO (ADR 0016, item 5; ADR 0015, adendo 3).
    O 404 uniforme vem de `professor_da_sessao`."""
    return professor_id


def atleta_visivel(session: Session, professor_id: int, atleta_id: int, agora: datetime) -> Atleta:
    """O atleta, se estiver no filtro; senao o mesmo `404` de atleta inexistente (nunca 403)."""
    atleta = session.scalars(
        select(Atleta).where(Atleta.id == atleta_id, Atleta.id.in_(atletas_do_professor(professor_id, agora)))
    ).first()
    if atleta is None:
        raise HTTPException(status_code=404, detail=ATLETA_NAO_ENCONTRADO["detail"])
    return atleta


def so_atletas_visiveis(consulta: Select, coluna_atleta_id, professor_id: int, agora: datetime) -> Select:
    """Aplica o filtro a uma consulta (`atividade.atleta_id`, `atleta.id`...): o jeito de uma rota de professor ler dados."""
    return consulta.where(coluna_atleta_id.in_(atletas_do_professor(professor_id, agora)))
