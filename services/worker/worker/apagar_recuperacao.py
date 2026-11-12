"""Apaga a recuperacao de um atleta (LGPD; issue #372, ADR 0014 item 5).

    uv run python -m worker.apagar_recuperacao --atleta "<nome>"

Apaga todas as noites de `recuperacao_dia` do atleta E os feedbacks dele com `recuperacao_importada_em IS NOT NULL` (o texto
gravado contem os valores da noite). O atleta, as atividades e os check-ins ficam; feedbacks sem recuperacao ficam. O worker
gera de novo os feedbacks apagados, sem a recuperacao, na proxima execucao. Idempotente. Imprime so contagens, nunca valores.
Se houver mais de um atleta com o nome, apaga so o de menor id e avisa.
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.recuperacao_banco import apagar_recuperacao_do_atleta
from sqlalchemy import select


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.apagar_recuperacao",
                                description="Apaga as noites de recuperacao (e os feedbacks que as usaram) de um atleta.")
    p.add_argument("--atleta", required=True, help="nome do atleta")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        atletas = session.scalars(select(Atleta).where(Atleta.nome == args.atleta).order_by(Atleta.id)).all()
        if not atletas:
            print("erro: atleta nao encontrado", file=sys.stderr)
            return 1
        if len(atletas) > 1:
            print(f"aviso: {len(atletas)} atletas com esse nome; apagado so o de menor id, os outros ficam", file=sys.stderr)
        n, f = apagar_recuperacao_do_atleta(session, atletas[0].id)
    print(f"recuperacao: apagadas={n}")
    print(f"feedbacks: apagados={f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
