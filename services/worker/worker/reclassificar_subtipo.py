"""Corrige o `subtipo` das atividades importadas com um mapeamento de tipos antigo (issue #183).

    uv run python -m worker.reclassificar_subtipo --exportacao CAMINHO [--atleta-id N] [--dry-run]

Relê o tipo da exportação Garmin (sem rede, sem tocar no banco na leitura), calcula o subtipo pelo `tipos.py` atual e
grava só onde o `subtipo` está NULL ou diverge. Casa pela chave `(fonte, fonte_id)` das linhas `garmin_export`.
Só mexe em `subtipo`, com uma exceção: se o novo subtipo é indoor, apaga `inicio_lat/lon` (indoor nunca guarda posição,
ADR 0007). Subtipo que a exportação não sabe dizer (`None`) nunca apaga um já gravado. Idempotente: a segunda rodada
muda 0. `--dry-run` calcula e imprime, mas não grava. Imprime as contagens por (subtipo antigo -> novo).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.db.models import Atividade
from app.ingestao.importacao import FONTE_EXPORTACAO
from app.ingestao.garmin import ler_exportacao
from app.ingestao.garmin.posicao import e_indoor
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class RelatorioSubtipo:
    mudancas: Counter = field(default_factory=Counter)  # (antigo, novo) -> quantas
    sem_posicao_apagada: int = 0  # viraram indoor e tinham posicao
    fora_da_exportacao: int = 0  # linhas garmin_export que a exportacao lida nao traz
    gravou: bool = False

    @property
    def total(self) -> int:
        return sum(self.mudancas.values())


def reclassificar_subtipo(session: Session, exportacao: str | Path, *, atleta_id: int | None = None,
                          dry_run: bool = False) -> RelatorioSubtipo:
    novos = {i.fonte_id: i.subtipo for i in ler_exportacao(exportacao) if i.fonte == FONTE_EXPORTACAO}
    consulta = select(Atividade).where(Atividade.fonte == FONTE_EXPORTACAO).order_by(Atividade.id)
    if atleta_id is not None:
        consulta = consulta.where(Atividade.atleta_id == atleta_id)
    rel = RelatorioSubtipo()
    for a in session.scalars(consulta):
        if a.fonte_id not in novos:
            rel.fora_da_exportacao += 1
            continue
        novo = novos[a.fonte_id]
        if novo is None or novo == a.subtipo:
            continue
        rel.mudancas[(a.subtipo, novo)] += 1
        if e_indoor(novo) and (a.inicio_lat is not None or a.inicio_lon is not None):
            rel.sem_posicao_apagada += 1
            if not dry_run:
                a.inicio_lat = a.inicio_lon = None
        if not dry_run:
            a.subtipo = novo
    if dry_run:
        session.rollback()
    else:
        session.commit()
        rel.gravou = True
    return rel


def imprimir(rel: RelatorioSubtipo, dry_run: bool) -> None:
    for (antigo, novo), n in sorted(rel.mudancas.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        print(f"{antigo or 'NULL'} -> {novo}: {n}")
    verbo = "mudariam (dry-run, nada gravado)" if dry_run else "mudaram"
    print(f"atividades que {verbo}: {rel.total}; posicao apagada por virar indoor: {rel.sem_posicao_apagada}; "
          f"fora da exportacao: {rel.fora_da_exportacao}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.reclassificar_subtipo",
        description="Preenche o subtipo (NULL ou divergente) pelo mapeamento de tipos atual. Sem rede.",
    )
    p.add_argument("--exportacao", required=True, help="exportacao Garmin (zip, pasta, JSON ou FIT)")
    p.add_argument("--atleta-id", type=int)
    p.add_argument("--dry-run", action="store_true", help="mostra as contagens sem gravar")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        rel = reclassificar_subtipo(session, args.exportacao, atleta_id=args.atleta_id, dry_run=args.dry_run)
    imprimir(rel, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
