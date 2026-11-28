"""Exclusao de conta e de todos os dados do atleta (issue #505, ADR 0016, item 9). Comando do operador, nunca rota.

`excluir_atleta` apaga, na ordem das chaves estrangeiras (sem depender de `ON DELETE CASCADE`, que o SQLite dos testes nao aplica):
conta e sessoes, tentativas de login do e-mail da conta, atividades e tudo que pende delas (segmentos, blocos, carga, clima, rotulo de
transicao, check-in e feedback), carga e recuperacao do atleta, limiares e zonas, recordes, semana-padrao, conversas e mensagens do chat (ADR 0017), vinculos, a trilha de
consentimento (`consentimento_evento`, padrao da ADR: apagada junto) e o proprio atleta. Os FIT guardados em disco saem depois do commit.
O professor e a assessoria NAO sao do atleta e ficam; o `tipo_confirmado_por` some junto com a atividade.

`TABELAS_APAGADAS` e a lista do que o codigo trata. Um teste percorre as chaves estrangeiras a partir de `atleta` e falha quando aparece
tabela nova sem tratamento aqui (ou sem ser declarada em `TABELAS_QUE_FICAM`).

Registro de exclusoes: antes de apagar, o operador grava uma linha `{atleta_id, data}` num arquivo FORA do banco (so ids e data, sem dado
pessoal). Restaurar um backup anterior a uma exclusao a ressuscitaria; `reaplicar_exclusoes` apaga de novo, antes de abrir a API.
Nada daqui escreve nome, e-mail ou valor de atleta em log ou na saida: so contagens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    Atividade, Atleta, BlocoAtividade, CargaAtividade, CargaGarminDia, CheckinTreino, ClimaAtividade, Conta, ConsentimentoEvento,
    Conversa, FeedbackTreino, LimiarAtleta, Mensagem, RecordePessoal, RecuperacaoDia, RotuloTransicao, Segmento, SemanaPadrao, SemanaPadraoItem, Sessao,
    TentativaLogin, VinculoProfessorAtleta, ZonaFcAtleta,
)
from app.ingestao.fit_guardado import pasta_fit
from app.servicos.conta import hash_do_email

# Ordem de apagar (filhos antes dos pais). Cada nome e o `__tablename__`.
TABELAS_APAGADAS = (
    "feedback_treino", "checkin_treino", "segmento", "bloco_atividade", "carga_atividade", "clima_atividade", "rotulo_transicao",
    "atividade", "carga_garmin_dia", "limiar_atleta", "recorde_pessoal", "recuperacao_dia", "zona_fc_atleta", "semana_padrao_item",
    "semana_padrao", "mensagem", "conversa", "consentimento_evento", "vinculo_professor_atleta", "sessao", "tentativa_login", "conta", "atleta",
)
# Tabelas que existem e NAO sao dados do atleta (nada delas e apagado aqui, de proposito).
TABELAS_QUE_FICAM = frozenset({"professor", "assessoria"})


class AtletaNaoEncontrado(LookupError):
    pass


@dataclass
class ResultadoExclusao:
    linhas: dict[str, int] = field(default_factory=dict)  # tabela -> linhas apagadas (so contagens)
    arquivos_fit: int = 0

    @property
    def total(self) -> int:
        return sum(self.linhas.values())


def _ids_atividade(atleta_id: int):
    return select(Atividade.id).where(Atividade.atleta_id == atleta_id)


def _ids_checkin(atleta_id: int):
    return select(CheckinTreino.id).where(CheckinTreino.atividade_id.in_(_ids_atividade(atleta_id)))


def _apagar(session: Session, resultado: ResultadoExclusao, modelo, condicao) -> None:
    n = session.execute(delete(modelo).where(condicao)).rowcount or 0
    resultado.linhas[modelo.__tablename__] = resultado.linhas.get(modelo.__tablename__, 0) + n


def registrar_exclusao(registro: Path, atleta_id: int, agora: datetime | None = None) -> None:
    """Acrescenta `{atleta_id, data}` ao registro (fora do banco). Sem nome, e-mail ou qualquer dado pessoal."""
    agora = agora or datetime.now(timezone.utc)
    registro.parent.mkdir(parents=True, exist_ok=True)
    with registro.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"atleta_id": atleta_id, "data": agora.date().isoformat()}) + "\n")
        f.flush()


def ler_registro(registro: Path) -> list[int]:
    if not registro.is_file():
        return []
    ids: list[int] = []
    for linha in registro.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            ids.append(int(json.loads(linha)["atleta_id"]))
    return ids


def excluir_atleta(session: Session, atleta_id: int, fit_dir: Path | None = None) -> ResultadoExclusao:
    """Apaga conta e dados do atleta e faz commit. `AtletaNaoEncontrado` se o id nao existe. Os FIT em disco saem depois do commit."""
    if session.get(Atleta, atleta_id) is None:
        raise AtletaNaoEncontrado()
    r = ResultadoExclusao()
    contas = select(Conta.id).where(Conta.atleta_id == atleta_id)
    emails = session.scalars(select(Conta.email).where(Conta.atleta_id == atleta_id)).all()
    atividades = _ids_atividade(atleta_id)
    # filhos das atividades
    _apagar(session, r, FeedbackTreino, FeedbackTreino.checkin_id.in_(_ids_checkin(atleta_id)))
    _apagar(session, r, CheckinTreino, CheckinTreino.atividade_id.in_(atividades))
    _apagar(session, r, Segmento, Segmento.atividade_id.in_(atividades))
    _apagar(session, r, BlocoAtividade, BlocoAtividade.atividade_id.in_(atividades))
    _apagar(session, r, CargaAtividade, CargaAtividade.atividade_id.in_(atividades))
    _apagar(session, r, ClimaAtividade, ClimaAtividade.atividade_id.in_(atividades))
    _apagar(session, r, RotuloTransicao, RotuloTransicao.atividade_id.in_(atividades))
    _apagar(session, r, Atividade, Atividade.atleta_id == atleta_id)
    # dado do atleta
    for modelo in (CargaGarminDia, LimiarAtleta, RecordePessoal, RecuperacaoDia, ZonaFcAtleta):
        _apagar(session, r, modelo, modelo.atleta_id == atleta_id)
    _apagar(session, r, SemanaPadraoItem, SemanaPadraoItem.semana_padrao_id.in_(select(SemanaPadrao.id).where(SemanaPadrao.atleta_id == atleta_id)))
    _apagar(session, r, SemanaPadrao, SemanaPadrao.atleta_id == atleta_id)
    _apagar(session, r, ConsentimentoEvento, ConsentimentoEvento.atleta_id == atleta_id)
    _apagar(session, r, VinculoProfessorAtleta, VinculoProfessorAtleta.atleta_id == atleta_id)
    # chat (ADR 0017): mensagens pela conversa, conversas pelo atleta
    _apagar(session, r, Mensagem, Mensagem.conversa_id.in_(select(Conversa.id).where(Conversa.atleta_id == atleta_id)))
    _apagar(session, r, Conversa, Conversa.atleta_id == atleta_id)
    # conta, sessoes e as tentativas de login do e-mail (guardadas so pelo hash dele)
    _apagar(session, r, Sessao, Sessao.conta_id.in_(contas))
    for e in emails:
        _apagar(session, r, TentativaLogin, TentativaLogin.email_hash == hash_do_email(e))
    _apagar(session, r, Conta, Conta.atleta_id == atleta_id)
    _apagar(session, r, Atleta, Atleta.id == atleta_id)
    session.commit()
    r.arquivos_fit = _apagar_fit(atleta_id, fit_dir)
    return r


def _apagar_fit(atleta_id: int, fit_dir: Path | None) -> int:
    pasta = pasta_fit(fit_dir) / str(atleta_id)
    n = 0
    if pasta.is_dir():
        for f in pasta.iterdir():
            if f.is_file():
                f.unlink()
                n += 1
        if not any(pasta.iterdir()):
            pasta.rmdir()
    return n


def reaplicar_exclusoes(session: Session, registro: Path, fit_dir: Path | None = None) -> list[int]:
    """Depois de restaurar um backup: apaga de novo os atletas do registro que ainda existem. Devolve os ids reapagados."""
    feitos: list[int] = []
    for atleta_id in dict.fromkeys(ler_registro(registro)):
        try:
            excluir_atleta(session, atleta_id, fit_dir)
        except AtletaNaoEncontrado:
            continue
        feitos.append(atleta_id)
    return feitos
