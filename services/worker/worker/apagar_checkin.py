"""Apaga os check-ins de um atleta (LGPD; issue #296, ADR 0012 item 5).

    uv run python -m worker.apagar_checkin --atleta "<nome>"

Apaga todos os check-ins das atividades do atleta (PSE, sensacao, atalhos e texto). O atleta e as atividades ficam.
Idempotente. Apaga tambem os feedbacks deles (ADR 0013, item 2). Imprime so a contagem, nunca valores. Se houver mais de um atleta com o nome, apaga so o de menor id
(o mesmo que o `apagar_saude` usa) e avisa que os outros ficam.
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.checkin import apagar_checkins_e_feedbacks_do_atleta
from sqlalchemy import select


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.apagar_checkin",
                                description="Apaga os check-ins pós-treino de um atleta.")
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
        n, f = apagar_checkins_e_feedbacks_do_atleta(session, atletas[0].id)
    print(f"checkins: apagados={n}")
    print(f"feedbacks: apagados={f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
