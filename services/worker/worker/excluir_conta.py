"""Exclusao de conta e restauracao com reaplicacao das exclusoes (issue #505, ADR 0016, item 9). Comandos do operador.

    uv run python -m worker.excluir_conta excluir --atleta 3 --confirmar 3 --registro /caminho/fora-do-banco/exclusoes.jsonl
    uv run python -m worker.excluir_conta reaplicar --registro /caminho/fora-do-banco/exclusoes.jsonl     # depois de restaurar um backup

`excluir` apaga a conta, as sessoes e TODOS os dados do atleta (atividades e o que pende delas, check-in, feedback, recuperacao, carga,
vinculos, trilha de consentimento, FIT guardados). Nao tem volta. Pede `--confirmar` com o mesmo id, para nao apagar por engano, e grava
o id e a data no registro (so isso, sem dado pessoal) ANTES de apagar. O registro fica FORA do banco que se restaura: e ele que deixa a
restauracao de um backup antigo nao ressuscitar o atleta.

Imprime so contagens por tabela, nunca nome, e-mail ou valores. Codigos de saida: 0 ok; 1 atleta nao encontrado ou confirmacao errada.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app.servicos import exclusao as ex


def _registro(args) -> Path | None:
    caminho = args.registro or os.environ.get("REGISTRO_EXCLUSOES")
    return Path(caminho) if caminho else None


def excluir(session, args) -> int:
    registro = _registro(args)
    if registro is None:
        print("erro: informe --registro (ou REGISTRO_EXCLUSOES): arquivo fora do banco com os ids excluidos", file=sys.stderr)
        return 1
    if args.confirmar != args.atleta:
        print("erro: --confirmar precisa repetir o id do atleta", file=sys.stderr)
        return 1
    from app.db.models import Atleta

    if session.get(Atleta, args.atleta) is None:
        print("erro: atleta nao encontrado", file=sys.stderr)
        return 1
    ex.registrar_exclusao(registro, args.atleta)
    r = ex.excluir_atleta(session, args.atleta, Path(args.fit_dir) if args.fit_dir else None)
    for tabela in ex.TABELAS_APAGADAS:
        if tabela in r.linhas:
            print(f"{tabela}: apagadas={r.linhas[tabela]}")
    print(f"arquivos_fit: apagados={r.arquivos_fit}")
    print("os backups antigos guardam o dado ate a retencao acabar (7 dias)")
    return 0


def reaplicar(session, args) -> int:
    registro = _registro(args)
    if registro is None:
        print("erro: informe --registro (ou REGISTRO_EXCLUSOES)", file=sys.stderr)
        return 1
    feitos = ex.reaplicar_exclusoes(session, registro, Path(args.fit_dir) if args.fit_dir else None)
    print(f"exclusoes no registro={len(set(ex.ler_registro(registro)))} reaplicadas={len(feitos)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.excluir_conta", description="Exclusao de conta e dados do atleta (operador).")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("excluir")
    e.add_argument("--atleta", type=int, required=True)
    e.add_argument("--confirmar", type=int, required=True)
    r = sub.add_parser("reaplicar")
    for x in (e, r):
        x.add_argument("--registro", help="arquivo de exclusoes, FORA do banco (ou REGISTRO_EXCLUSOES)")
        x.add_argument("--fit-dir", help="pasta dos FIT guardados (padrao: FIT_DIR)")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        return {"excluir": excluir, "reaplicar": reaplicar}[args.cmd](session, args)


if __name__ == "__main__":
    sys.exit(main())
