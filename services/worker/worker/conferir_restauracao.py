"""Confere um banco restaurado (issue #505, ADR 0016, item 9): contagem de linhas por tabela e, se pedido, uma conta que entra.

    uv run python -m worker.conferir_restauracao                          # so as contagens
    uv run python -m worker.conferir_restauracao --email a@exemplo.com    # tambem tenta entrar (a senha vem da entrada padrao)

Imprime `tabela: linhas=N` (ordem do modelo) e, com `--email`, `login: ok` ou `login: falhou`. Nunca imprime valores, e-mail, hash nem
token. O login de conferencia nao grava nada (a sessao criada e descartada). Codigos de saida: 0 ok; 1 login falhou.
"""

from __future__ import annotations

import argparse
import sys

from app.db import models  # noqa: F401
from app.db.base import Base
from app.servicos import conta as svc
from sqlalchemy import func, select


def contagens(session) -> dict[str, int]:
    return {t.name: session.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}


def login_ok(session, email: str, senha: str) -> bool:
    try:
        svc.entrar(session, email, senha)
    except (svc.CredencialInvalida, svc.ForcaBruta):
        session.rollback()
        return False
    session.rollback()  # descarta a sessao criada
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.conferir_restauracao", description="Confere um banco restaurado.")
    p.add_argument("--email", help="conta de teste para provar que entra; a senha vem da entrada padrao")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        for tabela, n in contagens(session).items():
            print(f"{tabela}: linhas={n}")
        if args.email:
            senha = sys.stdin.readline().rstrip("\n")
            ok = login_ok(session, args.email, senha)
            print(f"login: {'ok' if ok else 'falhou'}")
            return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
