"""Consentimento registrado pelo atleta (issue #501, ADR 0016, item 7).

- O vinculo (professor acompanha atleta) e do operador; o consentimento e so do atleta dono.
- `TERMO_VIGENTE` e a versao do termo que vale hoje. Mudar o texto sobe a versao e pede novo aceite: o vinculo com versao diferente
  da vigente vale como sem consentimento (o filtro `atletas_do_professor` confere).
- Aceitar grava `consentimento_em` e `termo_versao` JUNTOS, limpa `consentimento_revogado_em` e acrescenta um `consentimento_evento`.
  Revogar grava `consentimento_revogado_em` e acrescenta o evento; o vinculo e os dados do atleta ficam. Repetir o mesmo pedido nao
  grava nada de novo (nem evento).
- O termo e PROVISORIO e marcado (decisao 5 do Angelo): o texto definitivo vem da consulta de LGPD, antes do primeiro aluno real.
Nada aqui escreve nome, treino ou texto de atleta em log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsentimentoEvento, Professor, VinculoProfessorAtleta
from app.ingestao.garmin.unidades import para_utc

TERMO_VIGENTE = "termo@0-provisorio"
TERMO_PROVISORIO = True
# Rascunho sintetico da ADR 0016, item 7. Nao e aconselhamento juridico e vale so para o Angelo e dados sinteticos.
TERMO_TEXTO = (
    "Termo de consentimento (provisório). Ao aceitar, você autoriza o professor indicado a ver, no aplicativo, os seus treinos, o seu "
    "check-in (esforço percebido, sensação, atalhos e a observação que você escrever) e o feedback do treino, que pode citar o seu sono "
    "e a sua variabilidade da frequência cardíaca, para acompanhar a sua preparação. O professor não vê a sua carga de treino em "
    "números, a recuperação, o clima nem a sua semana-padrão, e não vê os dados de outros atletas; você também não vê os dos outros. "
    "Quando o feedback automático estiver ligado, um resumo do treino (números, sensação, esforço percebido e atalhos, entre eles o de "
    "dor, sem o seu nome e sem a observação que você escrever) é enviado a um serviço de inteligência artificial de terceiros, fora do "
    "Brasil, para redigir o feedback; esse envio não pode ser apagado por nós. Você pode revogar quando quiser, em Consentimento: a "
    "partir daí o professor deixa de ver os seus dados, mas o que ele já confirmou no seu treino (como o tipo) continua. Se você aceitar "
    "de novo, ele volta a ver todo o seu histórico. Revogar não apaga os seus dados: para apagar, peça ao operador. Estes são dados "
    "pessoais de saúde."
)


class VinculoNaoEncontrado(Exception):
    pass


class TermoDesatualizado(Exception):
    """A versao enviada nao e a vigente."""


@dataclass(frozen=True)
class VinculoOut:
    professor_id: int
    nome: str
    consentimento: bool  # ativo agora: aceito, nao revogado e na versao vigente
    termo_versao: str | None
    consentimento_em: datetime | None
    consentimento_revogado_em: datetime | None
    termo_desatualizado: bool  # aceitou uma versao que nao e mais a vigente: precisa aceitar de novo


def ativo(v: VinculoProfessorAtleta, agora: datetime) -> bool:
    """Mesma regra do filtro `atletas_do_professor` (que e quem decide de verdade; esta serve para o atleta ver o proprio estado)."""
    return (v.consentimento_em is not None and para_utc(v.consentimento_em) <= agora and v.consentimento_revogado_em is None
            and v.termo_versao == TERMO_VIGENTE)


def _saida(v: VinculoProfessorAtleta, nome: str, agora: datetime) -> VinculoOut:
    return VinculoOut(
        professor_id=v.professor_id, nome=nome, consentimento=ativo(v, agora), termo_versao=v.termo_versao,
        consentimento_em=v.consentimento_em, consentimento_revogado_em=v.consentimento_revogado_em,
        termo_desatualizado=(v.consentimento_em is not None and v.consentimento_revogado_em is None and v.termo_versao != TERMO_VIGENTE),
    )


def vinculos_do_atleta(session: Session, atleta_id: int, agora: datetime) -> list[VinculoOut]:
    linhas = session.execute(
        select(VinculoProfessorAtleta, Professor.nome).join(Professor, Professor.id == VinculoProfessorAtleta.professor_id)
        .where(VinculoProfessorAtleta.atleta_id == atleta_id).order_by(Professor.nome, Professor.id)
    ).all()
    return [_saida(v, nome, agora) for v, nome in linhas]


def _vinculo(session: Session, atleta_id: int, professor_id: int) -> tuple[VinculoProfessorAtleta, str]:
    linha = session.execute(
        select(VinculoProfessorAtleta, Professor.nome).join(Professor, Professor.id == VinculoProfessorAtleta.professor_id)
        .where(VinculoProfessorAtleta.atleta_id == atleta_id, VinculoProfessorAtleta.professor_id == professor_id)
    ).first()
    if linha is None:
        raise VinculoNaoEncontrado()
    return linha[0], linha[1]


def aceitar(session: Session, atleta_id: int, professor_id: int, termo_versao: str, agora: datetime) -> VinculoOut:
    """Nao faz commit. `VinculoNaoEncontrado` (sem vinculo criado pelo operador) ou `TermoDesatualizado`."""
    v, nome = _vinculo(session, atleta_id, professor_id)
    if termo_versao != TERMO_VIGENTE:
        raise TermoDesatualizado()
    if not ativo(v, agora):
        v.consentimento_em = agora
        v.termo_versao = TERMO_VIGENTE
        v.consentimento_revogado_em = None
        session.add(ConsentimentoEvento(atleta_id=atleta_id, professor_id=professor_id, acao="aceito", termo_versao=TERMO_VIGENTE,
                                        ocorrida_em=agora))
        session.flush()
    return _saida(v, nome, agora)


def revogar(session: Session, atleta_id: int, professor_id: int, agora: datetime) -> None:
    """Nao faz commit. So registra se havia consentimento a retirar (aceito e ainda nao revogado), seja qual for a versao."""
    v, _ = _vinculo(session, atleta_id, professor_id)
    if v.consentimento_em is not None and v.consentimento_revogado_em is None:
        v.consentimento_revogado_em = agora
        session.add(ConsentimentoEvento(atleta_id=atleta_id, professor_id=professor_id, acao="revogado",
                                        termo_versao=v.termo_versao or TERMO_VIGENTE, ocorrida_em=agora))
        session.flush()
