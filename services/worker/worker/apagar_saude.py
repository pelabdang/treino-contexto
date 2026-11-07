"""Apaga os dados de saude de um atleta (LGPD; issue #174, ADR 0010 item 3).

    uv run python -m worker.apagar_saude --atleta "<nome>"

Apaga limiar, zonas de FC, recordes pessoais e carga do Garmin do atleta. O atleta, as atividades e os FIT ficam.
Idempotente. Imprime so contagens por tabela, nunca valores. Se houver mais de um atleta com o nome, apaga so o de menor id
(o mesmo que o `importar_saude` usa).
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.ingestao.saude import apagar_saude_do_atleta
from sqlalchemy import select


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.apagar_saude",
                                description="Apaga limiar, zonas de FC, recordes e carga do Garmin de um atleta.")
    p.add_argument("--atleta", required=True, help="nome do atleta")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        atleta = session.scalars(select(Atleta).where(Atleta.nome == args.atleta).order_by(Atleta.id)).first()
        if atleta is None:
            print("erro: atleta nao encontrado", file=sys.stderr)
            return 1
        contagens = apagar_saude_do_atleta(session, atleta.id)
    for nome, n in contagens.items():
        print(f"saude {nome}: apagadas={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
