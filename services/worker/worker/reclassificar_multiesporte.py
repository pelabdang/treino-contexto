"""Marca o `subtipo` multiesporte nas atividades ja importadas (issue #230, ADR 0009).

    uv run python -m worker.reclassificar_multiesporte --exportacao CAMINHO [--atleta-id N] [--dry-run]

Relê o tipo da exportação Garmin (sem rede, sem tocar no banco na leitura) e, para as linhas `garmin_export` que o
`tipos.py` reconhece como multiesporte, grava `subtipo = multiesporte_pai` ou `troca`. Valores reconhecidos e fonte
pública: ver `app/ingestao/garmin/tipos.py`.

Só mexe em `subtipo`, e só de linhas com `modalidade = outra` cujo subtipo está vazio ou já é um dos dois
multiesporte (nunca sobrescreve outro subtipo, nunca muda modalidade, nunca descarta atividade). Idempotente: a segunda
rodada muda 0. `--dry-run` calcula e imprime sem gravar. O relatório traz as contagens por (subtipo antigo -> novo) e
quantas linhas do banco a exportação lida não traz, para conferir o que casou sem expor dado.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.db.models import Atividade
from app.ingestao.garmin import ler_exportacao
from app.ingestao.garmin.tipos import SUBTIPOS_MULTIESPORTE
from app.ingestao.importacao import FONTE_EXPORTACAO
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class RelatorioMultiesporte:
    mudancas: Counter = field(default_factory=Counter)  # (antigo, novo) -> quantas
    fora_da_exportacao: int = 0  # linhas garmin_export que a exportacao lida nao traz
    gravou: bool = False

    @property
    def total(self) -> int:
        return sum(self.mudancas.values())


def reclassificar_multiesporte(session: Session, exportacao: str | Path, *, atleta_id: int | None = None,
                               dry_run: bool = False) -> RelatorioMultiesporte:
    lidas = [i for i in ler_exportacao(exportacao) if i.fonte == FONTE_EXPORTACAO]
    todos = {i.fonte_id for i in lidas}
    novos = {i.fonte_id: i.subtipo for i in lidas if i.subtipo in SUBTIPOS_MULTIESPORTE}
    consulta = select(Atividade).where(Atividade.fonte == FONTE_EXPORTACAO).order_by(Atividade.id)
    if atleta_id is not None:
        consulta = consulta.where(Atividade.atleta_id == atleta_id)
    rel = RelatorioMultiesporte()
    for a in session.scalars(consulta):
        if a.fonte_id not in todos:
            rel.fora_da_exportacao += 1
            continue
        novo = novos.get(a.fonte_id)
        if novo is None or novo == a.subtipo or a.modalidade != "outra":
            continue
        if a.subtipo is not None and a.subtipo not in SUBTIPOS_MULTIESPORTE:
            continue
        rel.mudancas[(a.subtipo, novo)] += 1
        if not dry_run:
            a.subtipo = novo
    if dry_run:
        session.rollback()
    else:
        session.commit()
        rel.gravou = True
    return rel


def imprimir(rel: RelatorioMultiesporte, dry_run: bool) -> None:
    for (antigo, novo), n in sorted(rel.mudancas.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        print(f"{antigo or 'NULL'} -> {novo}: {n}")
    verbo = "mudariam (dry-run, nada gravado)" if dry_run else "mudaram"
    print(f"atividades que {verbo}: {rel.total}; fora da exportacao: {rel.fora_da_exportacao}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.reclassificar_multiesporte",
        description="Marca multiesporte_pai e troca no subtipo das atividades importadas. Sem rede.",
    )
    p.add_argument("--exportacao", required=True, help="exportacao Garmin (zip, pasta, JSON ou FIT)")
    p.add_argument("--atleta-id", type=int)
    p.add_argument("--dry-run", action="store_true", help="mostra as contagens sem gravar")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        rel = reclassificar_multiesporte(session, args.exportacao, atleta_id=args.atleta_id, dry_run=args.dry_run)
    imprimir(rel, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
