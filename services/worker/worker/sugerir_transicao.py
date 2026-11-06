"""Sugere o rotulo "treino de transicao" das atividades de um atleta (issue #157, ADR 0009).

    uv run python -m worker.sugerir_transicao --atleta-id <id>

Aplica a regra `transicao@N` (app.metricas.transicao) e grava em `rotulo_transicao`. Sem rede. Idempotente: rodar de
novo nao muda nada; a regra so grava "sim" e nunca toca numa linha de origem `atleta` (correcao do atleta). A importacao
e o upload de FIT ja chamam a mesma funcao para o atleta; este comando serve para a primeira vez no historico e depois
de uma versao nova da regra.
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.transicao import RelatorioTransicao, aplicar_sugestao
from sqlalchemy.orm import Session


class AtletaInexistente(LookupError):
    pass


def sugerir(session: Session, atleta_id: int) -> RelatorioTransicao:
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    return aplicar_sugestao(session, atleta_id)


def formatar(rel: RelatorioTransicao, atleta_id: int) -> str:
    return "\n".join(
        [
            f"transicao {rel.versao} do atleta {atleta_id}",
            f"atividades: {rel.atividades} (elegiveis: {rel.elegiveis})",
            f"sugeridas pela regra: {rel.sugeridas}",
            f"inseridas: {rel.inseridas}, atualizadas (versao nova): {rel.atualizadas}, "
            f"removidas: {rel.removidas}, sem mudanca: {rel.mantidas}",
            f"correcoes do atleta (nao tocadas): {rel.do_atleta} (em {rel.sugeridas_corrigidas} delas a regra sugere sim)",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.sugerir_transicao",
        description="Sugere o rótulo de treino de transição e grava no banco (nunca sobrescreve correção do atleta).",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            rel = sugerir(session, args.atleta_id)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(formatar(rel, args.atleta_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
