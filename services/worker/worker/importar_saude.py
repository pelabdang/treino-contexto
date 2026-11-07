"""Importa os dados de saude (limiar e zonas de FC) da exportacao Garmin para o banco (issue #140, ADR 0010).

    uv run python -m worker.importar_saude <caminho> --atleta "<nome>"

Sem rede. Idempotente. Serve a quem importou so o FIT ou importou a exportacao antes da Meta 6; o `importar_garmin` chama a
mesma funcao no fim. Imprime so contagens e avisos, nunca os valores (dado fisiologico, LGPD). Recordes e carga do Garmin: #174.
"""

from __future__ import annotations

import argparse
import sys

from app.ingestao.saude import RelatorioSaude, importar_saude

__all__ = ["RelatorioSaude", "importar_saude", "imprimir", "main"]


def imprimir(rel: RelatorioSaude) -> None:
    for nome, c in (("limiar", rel.limiar), ("zonas", rel.zonas)):
        print(f"saude {nome}: inseridas={c.inseridas} atualizadas={c.atualizadas} ignoradas={c.ignoradas}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.importar_saude",
                                description="Importa limiar e zonas de FC da exportacao Garmin (zip ou pasta).")
    p.add_argument("caminho")
    p.add_argument("--atleta", required=True, help="nome do atleta (criado se houver dados de saude)")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            rel = importar_saude(session, args.caminho, args.atleta)
    except FileNotFoundError:
        print("erro: caminho nao encontrado", file=sys.stderr)
        return 1
    imprimir(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
