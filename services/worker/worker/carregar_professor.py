"""Carrega o professor e os atletas FICTICIOS do piloto da Meta 11 de uma pasta de fixtures (issue #423, ADR 0015).

    uv run python -m worker.carregar_professor --fixtures tests/fixtures/professor_piloto

Le `<pasta>/identidade.json`: `assessoria`, `professores` (lista de `{nome}`), `professor_do_piloto` (o nome de um deles) e
`atletas` (lista de `{nome, vinculos: [{professor, consentimento_em}]}`; `consentimento_em` e texto ISO com fuso ou `null`).
Grava so a identidade e os vinculos (as atividades, check-ins e noites sinteticos entram pelos outros comandos). Idempotente:
acha assessoria, professor e atleta pelo nome e atualiza o consentimento. Recusa (codigo 1, mensagem fixa) um atleta que ja
existe com o mesmo nome mas nao veio desta carga (nao esta na assessoria da fixture), para nunca misturar dado
sintetico com dado real. A saida tem so contagens e a linha `PROFESSOR_ID=<id>` (so informativa: a API ignora essa variavel desde a #500; o professor vem da sessao).

Codigos de saida: 0 ok; 1 argumento, fixture invalida ou atleta que nao e da fixture.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.db.models import Assessoria, Atleta, Professor, VinculoProfessorAtleta
from app.servicos.consentimento import TERMO_VIGENTE
from sqlalchemy import select
from sqlalchemy.orm import Session


class FixtureInvalida(Exception):
    """Mensagem fixa, sem trecho do arquivo."""


def _ler(pasta: Path) -> dict:
    arq = pasta / "identidade.json"
    if not arq.is_file():
        raise FixtureInvalida("identidade.json nao encontrado na pasta")
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        nomes = [p["nome"] for p in dados["professores"]]
        assert isinstance(dados["assessoria"], str) and dados["professor_do_piloto"] in nomes and len(set(nomes)) == len(nomes)
        atletas = [a["nome"] for a in dados["atletas"]]
        assert len(set(atletas)) == len(atletas)
        for a in dados["atletas"]:
            for v in a.get("vinculos", []):
                assert v["professor"] in nomes
                if v.get("consentimento_em") is not None:
                    if datetime.fromisoformat(v["consentimento_em"]).tzinfo is None:
                        raise ValueError
    except (KeyError, TypeError, ValueError, AssertionError, json.JSONDecodeError):
        raise FixtureInvalida("identidade.json fora do formato esperado") from None
    return dados


def carregar(session: Session, dados: dict) -> tuple[int, int, int, int]:
    """Grava e devolve (id do professor do piloto, professores, atletas, vinculos). Nao faz commit."""
    assessoria = session.scalars(select(Assessoria).where(Assessoria.nome == dados["assessoria"])).first()
    if assessoria is None:
        assessoria = Assessoria(nome=dados["assessoria"])
        session.add(assessoria)
        session.flush()
    professores: dict[str, Professor] = {}
    for p in dados["professores"]:
        prof = session.scalars(
            select(Professor).where(Professor.nome == p["nome"], Professor.assessoria_id == assessoria.id)).first()
        if prof is None:
            prof = Professor(assessoria_id=assessoria.id, nome=p["nome"])
            session.add(prof)
            session.flush()
        professores[p["nome"]] = prof
    n_atletas = n_vinculos = 0
    for a in dados["atletas"]:
        atleta = session.scalars(select(Atleta).where(Atleta.nome == a["nome"]).order_by(Atleta.id)).first()
        if atleta is not None:
            da_carga = atleta.assessoria_id == assessoria.id  # a carga cria o atleta na assessoria da fixture
            if not da_carga:
                raise FixtureInvalida("ja existe um atleta com o nome de um da fixture que nao veio desta carga")
        else:
            atleta = Atleta(assessoria_id=assessoria.id, nome=a["nome"])
            session.add(atleta)
            session.flush()
        n_atletas += 1
        for v in a.get("vinculos", []):
            quando = datetime.fromisoformat(v["consentimento_em"]) if v.get("consentimento_em") else None
            vinculo = session.get(VinculoProfessorAtleta, (professores[v["professor"]].id, atleta.id))
            if vinculo is None:
                session.add(VinculoProfessorAtleta(professor_id=professores[v["professor"]].id, atleta_id=atleta.id,
                                                   consentimento_em=quando, termo_versao=TERMO_VIGENTE if quando else None))
            else:
                vinculo.consentimento_em = quando
                vinculo.termo_versao = TERMO_VIGENTE if quando else None
                vinculo.consentimento_revogado_em = None
            n_vinculos += 1
    session.flush()
    return professores[dados["professor_do_piloto"]].id, len(professores), n_atletas, n_vinculos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.carregar_professor",
                                description="Carrega o professor e os atletas ficticios do piloto da Meta 11.")
    p.add_argument("--fixtures", type=Path, required=True, help="pasta com identidade.json (dado sintetico)")
    args = p.parse_args(argv)
    try:
        dados = _ler(args.fixtures)
    except FixtureInvalida as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        try:
            pid, n_prof, n_atl, n_vin = carregar(session, dados)
        except FixtureInvalida as e:
            session.rollback()
            print(f"erro: {e}", file=sys.stderr)
            return 1
        session.commit()
    print(f"professores={n_prof} atletas={n_atl} vinculos={n_vin}")
    print(f"PROFESSOR_ID={pid}  (cole no .env local)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
