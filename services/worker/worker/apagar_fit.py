"""Apaga os FIT enviados por upload de um atleta (issue #94, ADR 0006).

    uv run python -m worker.apagar_fit --atleta-id <id>

Apaga os arquivos de `FIT_DIR/<id>/` e limpa `atividade.arquivo_bruto` das atividades que apontavam para eles.
As atividades, os segmentos e a serie ficam. Idempotente.
"""

from __future__ import annotations

import argparse
import sys

from app.ingestao.fit_guardado import AtletaInexistente, apagar_do_atleta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.apagar_fit",
        description="Apaga os FIT guardados de um atleta e limpa arquivo_bruto, sem apagar as atividades.",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            arquivos, atividades = apagar_do_atleta(session, args.atleta_id)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(f"apagados {arquivos} arquivos; arquivo_bruto limpo em {atividades} atividades do atleta {args.atleta_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
