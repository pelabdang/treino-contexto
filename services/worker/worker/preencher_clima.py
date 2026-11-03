"""Preenche posicao e clima das atividades (Meta 4, ADR 0007, itens 7 e 8).

    uv run python -m worker.preencher_clima [--atleta-id N] [--exportacao CAMINHO] [--limite N]
                                            [--refazer-falhas] [--so-posicao]

1. Posicao: relê o FIT guardado em `FIT_DIR` e, com `--exportacao`, a exportacao. So preenche onde esta NULL.
2. Clima (Open-Meteo, so posicao arredondada e horario): ao ar livre, com posicao, sem clima `ok` valido e com fim a
   mais de 7 dias. Sequencial, com pausa, teto por rodada, um `commit` por atividade. Idempotente.
`--so-posicao` nao chama a rede. Imprime quantas posicoes preencheu e quantas atividades ficaram em cada estado.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.clima import ClienteClima
from app.servicos.clima import (
    LIMITE_PADRAO,
    PAUSA_S,
    RelatorioClima,
    contar_estados,
    preencher_clima,
    preencher_posicoes,
)
from sqlalchemy.orm import Session


def rodar(session: Session, cliente: ClienteClima | None, *, atleta_id: int | None = None, exportacao=None,
          limite: int = LIMITE_PADRAO, refazer_falhas: bool = False, so_posicao: bool = False,
          fit_dir=None, dormir=None, pausa_s: float = PAUSA_S) -> tuple[int, dict[str, int], RelatorioClima | None]:
    """(posicoes preenchidas, atividades por estado, relatorio do clima ou None com `so_posicao`)."""
    posicoes = preencher_posicoes(session, atleta_id=atleta_id, exportacao=exportacao, fit_dir=fit_dir)
    relatorio = None
    if not so_posicao:
        extra = {} if dormir is None else {"dormir": dormir}
        relatorio = preencher_clima(session, cliente, atleta_id=atleta_id, limite=limite,
                                    refazer_falhas=refazer_falhas, pausa_s=pausa_s, **extra)
    return posicoes, contar_estados(session, atleta_id), relatorio


def imprimir(posicoes: int, estados: dict[str, int], relatorio: RelatorioClima | None) -> None:
    print(f"posicoes preenchidas={posicoes}")
    if relatorio is not None:
        aviso = (" (rodada parada: limite de chamadas da API)" if relatorio.parou
                 else " (teto da rodada atingido)" if relatorio.atingiu_limite else "")
        print(f"chamadas={relatorio.chamadas}{aviso}")
    print(" ".join(f"{k}={v}" for k, v in estados.items()))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.preencher_clima",
                                description="Preenche a posicao de inicio e o clima das atividades.")
    p.add_argument("--atleta-id", type=int)
    p.add_argument("--exportacao", help="exportacao Garmin (zip, pasta, JSON ou FIT) para reler a posicao")
    p.add_argument("--limite", type=int, default=LIMITE_PADRAO, help="teto de chamadas por rodada")
    p.add_argument("--refazer-falhas", action="store_true")
    p.add_argument("--so-posicao", action="store_true", help="so preenche a posicao; nao chama a rede")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    from app.db.session import SessionLocal  # usa DATABASE_URL

    cliente = None
    if not args.so_posicao:
        from app.clima import ClienteOpenMeteo

        cliente = ClienteOpenMeteo()
    with SessionLocal() as session:
        imprimir(*rodar(session, cliente, atleta_id=args.atleta_id, exportacao=args.exportacao, limite=args.limite,
                        refazer_falhas=args.refazer_falhas, so_posicao=args.so_posicao))
    return 0


if __name__ == "__main__":
    sys.exit(main())
