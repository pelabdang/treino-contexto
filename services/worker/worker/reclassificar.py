"""Reclassifica as corridas de um atleta com a regra atual dos tiros (issue #64, ADR 0004).

    uv run python -m worker.reclassificar --atleta-id <id>

Chama `classificar_atividades` (idempotente) e mostra quantas corridas processou. Serve para quando
`reclassificacao_pendente` vem `true` na API: a API nunca reclassifica na leitura. Depois do comando
o campo volta a `false`. Reimportar a exportação Garmin tem o mesmo efeito.
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.evolucao_tiros import classificar_atividades
from sqlalchemy.orm import Session


class AtletaInexistente(LookupError):
    pass


def reclassificar(session: Session, atleta_id: int) -> int:
    """Reclassifica as corridas do atleta e devolve quantas processou."""
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    return classificar_atividades(session, atleta_id)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.reclassificar",
        description="Reclassifica as corridas do atleta com a regra atual dos tiros de 1 km.",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            n = reclassificar(session, args.atleta_id)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(f"reclassificadas {n} corridas do atleta {args.atleta_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
