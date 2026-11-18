"""Comandos do operador para contas (issue #499, ADR 0016, item 6). Sem painel e sem rota de administracao.

    uv run python -m worker.conta criar --email a@exemplo.com --atleta 3        # pede a senha, sem eco
    uv run python -m worker.conta criar --email p@exemplo.com --professor 1 --gerar-senha-temporaria
    uv run python -m worker.conta vincular --professor 1 --atleta 3             # vinculo SEM consentimento
    uv run python -m worker.conta redefinir-senha --email a@exemplo.com         # senha temporaria, mostrada uma vez
    uv run python -m worker.conta desativar --email a@exemplo.com
    uv run python -m worker.conta limpar                                        # sessoes vencidas e tentativas de mais de 30 dias

A senha nunca e argumento de linha de comando (iria para o historico do shell): sai de um prompt sem eco, da entrada padrao (`--senha-stdin`,
para roteiro) ou e gerada (`--gerar-senha-temporaria`, que tambem obriga a troca no primeiro acesso). O e-mail e a senha nunca vao a log; a
saida de erro tem mensagem fixa. A senha temporaria e a unica coisa sensivel que sai, uma vez, no terminal.

Codigos de saida: 0 ok; 1 argumento ou dado invalido; 2 senha que nao serve.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.db.models import Atleta, Professor, VinculoProfessorAtleta
from app.servicos import conta as svc


def _senha(args) -> tuple[str, bool]:
    """(senha, temporaria)"""
    if args.gerar_senha_temporaria:
        return svc.senha_temporaria(), True
    if args.senha_stdin:
        return sys.stdin.readline().rstrip("\n"), False
    a = getpass.getpass("Senha: ")
    if a != getpass.getpass("Repita a senha: "):
        raise svc.ContaInvalida("as senhas nao conferem")
    return a, False


def criar(session, args) -> int:
    senha, temporaria = _senha(args)
    try:
        svc.criar_conta(session, args.email, senha, atleta_id=args.atleta, professor_id=args.professor,
                        deve_trocar_senha=temporaria)
    except svc.SenhaInvalida:
        print("erro: a senha nao serve (minimo de 10 caracteres, nao pode ser comum nem igual ao e-mail)", file=sys.stderr)
        return 2
    except svc.ContaInvalida as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    session.commit()
    print("conta criada")
    if temporaria:
        print(f"senha temporaria (mostrada uma vez): {senha}")
    return 0


def vincular(session, args) -> int:
    if session.get(Professor, args.professor) is None or session.get(Atleta, args.atleta) is None:
        print("erro: professor ou atleta nao encontrado", file=sys.stderr)
        return 1
    if session.get(VinculoProfessorAtleta, (args.professor, args.atleta)) is None:
        session.add(VinculoProfessorAtleta(professor_id=args.professor, atleta_id=args.atleta))  # sem consentimento: e do atleta
        session.commit()
    print("vinculo criado, sem consentimento")
    return 0


def redefinir(session, args) -> int:
    c = svc.conta_por_email(session, args.email)
    if c is None:
        print("erro: conta nao encontrada", file=sys.stderr)
        return 1
    nova = svc.redefinir_senha(session, c)
    session.commit()
    print(f"senha temporaria (mostrada uma vez): {nova}")
    return 0


def desativar(session, args) -> int:
    c = svc.conta_por_email(session, args.email)
    if c is None:
        print("erro: conta nao encontrada", file=sys.stderr)
        return 1
    svc.desativar(session, c)
    session.commit()
    print("conta desativada, sessoes revogadas")
    return 0


def limpar(session, args) -> int:
    s, t = svc.limpar_expiradas(session)
    session.commit()
    print(f"sessoes apagadas={s} tentativas apagadas={t}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.conta", description="Contas de login (operador).")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar")
    c.add_argument("--email", required=True)
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--atleta", type=int)
    g.add_argument("--professor", type=int)
    s = c.add_mutually_exclusive_group()
    s.add_argument("--senha-stdin", action="store_true")
    s.add_argument("--gerar-senha-temporaria", action="store_true")
    v = sub.add_parser("vincular")
    v.add_argument("--professor", type=int, required=True)
    v.add_argument("--atleta", type=int, required=True)
    for nome in ("redefinir-senha", "desativar"):
        x = sub.add_parser(nome)
        x.add_argument("--email", required=True)
    sub.add_parser("limpar")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    acao = {"criar": criar, "vincular": vincular, "redefinir-senha": redefinir, "desativar": desativar, "limpar": limpar}[args.cmd]
    with SessionLocal() as session:
        return acao(session, args)


if __name__ == "__main__":
    sys.exit(main())
