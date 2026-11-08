"""Gera o gráfico e o CSV da carga de treino (CTL, ATL, TSB e carga diária) de um atleta (issue #143).

    uv run python -m worker.grafico_carga --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD]

Só lê o banco (``carga_atividade``, gravada por ``worker.calcular_carga``) e grava, em ``entregas/meta-6/``
(fora do git: o gráfico com dado real é pessoal):
  carga-atleta-<id>.png   (``render_png``)
  carga-atleta-<id>.csv   (``linhas_csv``, a mesma série)
A série é calculada desde o primeiro dia; ``--inicio``/``--fim`` só recortam o que se desenha (o CTL de um recorte
continua sendo o da série inteira). Formato em docs/modulos/grafico-carga.md. Sem rede.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from app.db.models import Atleta
from app.graficos.carga import COLUNAS_CSV, linhas_csv, render_png
from app.servicos.serie_carga_banco import serie_carga_do_atleta
from sqlalchemy.orm import Session

PASTA_PADRAO = Path("entregas") / "meta-6"


class AtletaInexistente(LookupError):
    pass


def gerar(
    session: Session,
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    pasta: Path = PASTA_PADRAO,
) -> tuple[Path, Path, int]:
    """Grava o PNG e o CSV e devolve os dois caminhos e quantas atividades estão sem linha de carga."""
    atleta = session.get(Atleta, atleta_id)
    if atleta is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    lida = serie_carga_do_atleta(session, atleta_id)
    dias = [d for d in lida.serie.dias if (inicio is None or d.dia >= inicio) and (fim is None or d.dia <= fim)]

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"carga-atleta-{atleta_id}"
    png, arq_csv = base.with_suffix(".png"), base.with_suffix(".csv")
    png.write_bytes(render_png(dias, atleta.nome))
    with arq_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_CSV, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas_csv(dias))
    return png, arq_csv, lida.sem_linha


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data inválida: {texto!r} (use AAAA-MM-DD)") from None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m worker.grafico_carga",
        description="Gera o PNG e o CSV da carga de treino (estimativa) em entregas/meta-6/.",
    )
    p.add_argument("--atleta-id", type=int, required=True)
    p.add_argument("--inicio", type=_data, help="AAAA-MM-DD (data local, inclusiva)")
    p.add_argument("--fim", type=_data, help="AAAA-MM-DD (data local, inclusiva)")
    p.add_argument("--saida", type=Path, default=PASTA_PADRAO, help="pasta de saída (padrão: entregas/meta-6)")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            png, arq_csv, sem_linha = gerar(session, args.atleta_id, args.inicio, args.fim, args.saida)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    if sem_linha:
        print(f"aviso: {sem_linha} atividade(s) sem carga gravada; rode worker.calcular_carga", file=sys.stderr)
    print(f"gravado: {png}\ngravado: {arq_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
