"""Carrega o professor e os atletas SINTETICOS do piloto, com contas de teste (issue #506, ADR 0016, itens 6 e 10). Comando do operador.

    uv run python -m worker.carregar_piloto --fixtures tests/fixtures/professor_piloto [--dominio piloto.exemplo.com] [--sem-consentimento]

Faz o que `worker.carregar_professor` faz (assessoria, professores, atletas e vinculos da fixture) e cria UMA conta para cada professor e
cada atleta da fixture, com e-mail sintetico (`<papel>-<id>@<dominio>`) e senha temporaria aleatoria que obriga a troca no primeiro acesso.
As senhas saem UMA vez no terminal, nunca em arquivo, log ou repositorio: anote-as fora do git. Idempotente: conta que ja existe nao e
recriada e nao ganha senha nova (para isso, `worker.conta redefinir-senha`). `--sem-consentimento` ignora os consentimentos da fixture e
deixa todos os vinculos "aguardando o atleta" (o consentimento e ato do atleta, ADR 0016, item 7).

O que este comando NAO faz: carregar historico real. O historico do Angelo so entra no servidor depois da restauracao testada (#505), e
e carregado por ele ou pelo Theo com os importadores de sempre, com nada no repositorio, em issue, PR ou log (decisao 7). Por seguranca,
a carga recusa um atleta que ja exista com o nome de um da fixture mas nao tenha vindo desta carga.

Codigos de saida: 0 ok; 1 argumento, fixture invalida ou atleta que nao e da fixture.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from app.db.models import Atleta, Conta, Professor
from app.servicos import conta as svc
from sqlalchemy import select

from worker import carregar_professor as cp

_DOMINIO = re.compile(r"[a-z0-9]([a-z0-9.-]{0,60}[a-z0-9])?\.[a-z]{2,}")


def _email(papel: str, id_: int, dominio: str) -> str:
    return f"{papel}-{id_}@{dominio}"


def criar_contas(session, dados: dict, dominio: str) -> list[tuple[str, str]]:
    """Uma conta por professor e por atleta da fixture. Devolve [(e-mail, senha temporaria)] so das contas NOVAS. Nao faz commit."""
    novas: list[tuple[str, str]] = []
    assessoria_nomes_prof = [p["nome"] for p in dados["professores"]]
    pessoas = [("professor", p) for p in session.scalars(select(Professor).where(Professor.nome.in_(assessoria_nomes_prof))
                                                          .order_by(Professor.id))]
    pessoas += [("atleta", a) for a in session.scalars(select(Atleta).where(Atleta.nome.in_([a["nome"] for a in dados["atletas"]]))
                                                       .order_by(Atleta.id))]
    for papel, pessoa in pessoas:
        campo = {"professor_id": pessoa.id} if papel == "professor" else {"atleta_id": pessoa.id}
        if session.scalar(select(Conta.id).where(getattr(Conta, f"{papel}_id") == pessoa.id)) is not None:
            continue
        email = _email(papel, pessoa.id, dominio)
        senha = svc.senha_temporaria()
        svc.criar_conta(session, email, senha, deve_trocar_senha=True, **campo)
        novas.append((email, senha))
    return novas


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.carregar_piloto",
                                description="Carrega o professor e os atletas sinteticos do piloto, com contas de teste.")
    p.add_argument("--fixtures", type=Path, required=True, help="pasta com identidade.json (dado sintetico)")
    p.add_argument("--dominio", default="piloto.exemplo.com", help="dominio dos e-mails sinteticos das contas")
    p.add_argument("--sem-consentimento", action="store_true", help="ignora os consentimentos da fixture (todos aguardam o atleta)")
    args = p.parse_args(argv)
    if not _DOMINIO.fullmatch(args.dominio):
        print("erro: dominio invalido", file=sys.stderr)
        return 1
    try:
        dados = cp._ler(args.fixtures)
    except cp.FixtureInvalida as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    if args.sem_consentimento:
        for a in dados["atletas"]:
            for v in a.get("vinculos", []):
                v["consentimento_em"] = None

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        try:
            _, n_prof, n_atl, n_vin = cp.carregar(session, dados)
            novas = criar_contas(session, dados, args.dominio)
        except cp.FixtureInvalida as e:
            session.rollback()
            print(f"erro: {e}", file=sys.stderr)
            return 1
        except (svc.ContaInvalida, svc.SenhaInvalida):
            session.rollback()
            print("erro: nao foi possivel criar as contas (dominio ou dado invalido)", file=sys.stderr)
            return 1
        session.commit()
    print(f"professores={n_prof} atletas={n_atl} vinculos={n_vin} contas_novas={len(novas)}")
    if novas:
        print("contas de teste (senha temporaria, mostrada UMA vez; anote fora do git):")
        for email, senha in novas:
            print(f"  {email}  {senha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
