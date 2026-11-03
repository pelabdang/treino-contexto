"""Importa a exportacao Garmin para o banco (issue #13).

    uv run python -m worker.importar_garmin <caminho> --atleta "<nome>"

Idempotente: a chave de `atividade` e (atleta_id, fonte, fonte_id) (ADR 0001), mais a regra dos 60 s da ADR 0006.
A gravacao mora na API (`app.ingestao.importacao`); aqui fica so a linha de comando. Os nomes abaixo continuam
exportados daqui para quem ja importava deste modulo.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.ingestao.importacao import (  # noqa: F401
    RelatorioImportacao,
    fuso_min,
    importar,
    normalizar_intensidade,
    pace_s_km,
)

__all__ = ["RelatorioImportacao", "fuso_min", "importar", "main", "normalizar_intensidade", "pace_s_km"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.importar_garmin",
                                description="Importa a exportacao Garmin (zip, pasta, JSON ou FIT) no banco.")
    p.add_argument("caminho")
    p.add_argument("--atleta", required=True, help="nome do atleta (criado se nao existir)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        rel = importar(session, args.caminho, args.atleta)
    print(f"inseridas={rel.inseridas} atualizadas={rel.atualizadas} ignoradas={rel.ignoradas} "
          f"avisos={len(rel.avisos)}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
