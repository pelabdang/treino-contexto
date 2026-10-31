"""Gera o gráfico e o CSV da evolução dos tiros de 1 km de um atleta (issue #15).

    uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD]

Lê a série do banco (``serie_tiros_1km``, #14) e grava, em ``entregas/meta-1/``
(fora do git: o gráfico com dado real é pessoal):
  tiros-1km-atleta-<id>.png   (``render_png``, #39)
  tiros-1km-atleta-<id>.csv   (``linhas_csv``, #39)
Não desenha nem formata nada aqui: o formato está em docs/modulos/grafico-tiros.md.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from app.db.models import Atleta
from app.graficos.tiros_1km import COLUNAS_CSV, linhas_csv, render_png
from app.servicos.evolucao_tiros import serie_tiros_1km
from sqlalchemy.orm import Session

PASTA_PADRAO = Path("entregas") / "meta-1"


class AtletaInexistente(LookupError):
    pass


def gerar(
    session: Session,
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    pasta: Path = PASTA_PADRAO,
) -> tuple[Path, Path]:
    """Grava o PNG e o CSV do atleta e devolve os dois caminhos."""
    atleta = session.get(Atleta, atleta_id)
    if atleta is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    serie = serie_tiros_1km(session, atleta_id, inicio, fim)

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"tiros-1km-atleta-{atleta_id}"
    png = base.with_suffix(".png")
    arq_csv = base.with_suffix(".csv")
    png.write_bytes(render_png(serie, atleta.nome))
    with arq_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_CSV, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas_csv(serie))
    return png, arq_csv


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data inválida: {texto!r} (use AAAA-MM-DD)") from None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.grafico_tiros_1km",
        description="Gera o PNG e o CSV da evolução dos tiros de 1 km em entregas/meta-1/.",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    p.add_argument("--inicio", type=_data, help="AAAA-MM-DD (data local, inclusiva)")
    p.add_argument("--fim", type=_data, help="AAAA-MM-DD (data local, inclusiva)")
    p.add_argument("--saida", type=Path, default=PASTA_PADRAO, help="pasta de saída (padrão: entregas/meta-1)")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            png, arq_csv = gerar(session, args.atleta_id, args.inicio, args.fim, args.saida)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(f"gravado: {png}\ngravado: {arq_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
