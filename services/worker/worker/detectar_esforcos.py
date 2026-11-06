"""Detecta blocos e esforços das corridas e pedaladas de um atleta (issue #166, ADR 0008).

    uv run python -m worker.detectar_esforcos --atleta-id <id>

Grava em `bloco_atividade` (um bloco por linha, todas as categorias). Sem rede. Idempotente: rodar de novo não muda
nada; mudar a `VERSAO` de `app.metricas.esforcos` (ou qualquer constante da regra) redetecta tudo. A importação e o
upload de FIT já chamam a mesma detecção para as atividades que entram ou mudam; este comando serve para reprocessar
o histórico inteiro (primeira vez, ou depois de uma versão nova da regra).
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.servicos.esforcos import RelatorioEsforcos, detectar_esforcos
from sqlalchemy.orm import Session


class AtletaInexistente(LookupError):
    pass


def detectar(session: Session, atleta_id: int) -> RelatorioEsforcos:
    """Detecta os esforços das atividades do atleta e devolve o relatório da rodada."""
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    return detectar_esforcos(session, atleta_id)


def formatar(rel: RelatorioEsforcos, atleta_id: int) -> str:
    linhas = [
        f"esforcos {rel.versao} do atleta {atleta_id}",
        f"atividades processadas: {rel.processadas} (gravadas de novo: {rel.alteradas}, "
        f"sem mudança: {rel.inalteradas}, sem blocos: {rel.sem_blocos})",
    ]
    for modalidade in ("corrida", "ciclismo"):
        linhas.append(
            f"{modalidade}: esforcos={rel.esforcos[modalidade]} treinos-chave={rel.treinos_chave[modalidade]}"
        )
    if rel.por_faixa:
        faixas = ", ".join(f"{k}={v}" for k, v in sorted(rel.por_faixa.items()))
        linhas.append(f"esforcos por faixa: {faixas}")
    if rel.referencia_da_atividade:
        linhas.append(
            f"referencia da propria atividade (sem historico): {rel.referencia_da_atividade} atividades"
        )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.detectar_esforcos",
        description="Detecta blocos e esforços (corrida por distância, ciclismo por duração) e grava no banco.",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            rel = detectar(session, args.atleta_id)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(formatar(rel, args.atleta_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
