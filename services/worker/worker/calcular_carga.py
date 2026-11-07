"""Calcula a carga de treino (rTSS/hrTSS por volta) das atividades de um atleta (issue #141, ADR 0010).

    uv run python -m worker.calcular_carga --atleta-id <id>

Grava em `carga_atividade`. Sem rede. Idempotente: rodar de novo não muda nada; subir a `VERSAO` de
`app.metricas.carga` recalcula tudo; um limiar novo recalcula só as atividades cujo limiar usado mudou. O
`importar_garmin` chama o mesmo cálculo depois dos dados de saúde. Imprime só contagens, nunca limiar nem FC (LGPD).
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.carga import RelatorioCarga, calcular_carga_do_atleta
from sqlalchemy.orm import Session

__all__ = ["AtletaInexistente", "RelatorioCarga", "calcular", "formatar", "main"]


class AtletaInexistente(LookupError):
    pass


def calcular(session: Session, atleta_id: int) -> RelatorioCarga:
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    return calcular_carga_do_atleta(session, atleta_id)


def formatar(rel: RelatorioCarga, atleta_id: int) -> str:
    linhas = [
        f"carga {rel.versao} do atleta {atleta_id}",
        f"atividades processadas: {rel.processadas} (gravadas: {rel.gravadas}, já atualizadas: {rel.inalteradas})",
        f"calculadas: {rel.calculadas}",
        f"sem carga: {rel.sem_carga_total}",
    ]
    linhas += [f"  {motivo}: {n}" for motivo, n in rel.sem_carga.items() if n]
    linhas.append(f"ignoradas (multiesporte e troca, sem linha): {rel.ignoradas_multiesporte}"
                  + (f" (linhas removidas: {rel.removidas})" if rel.removidas else ""))
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.calcular_carga",
                                description="Calcula e grava a carga de treino por atividade (sem rede).")
    p.add_argument("--atleta-id", type=int, required=True)
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            rel = calcular(session, args.atleta_id)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(formatar(rel, args.atleta_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
