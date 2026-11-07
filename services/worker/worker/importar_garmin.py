"""Importa a exportacao Garmin para o banco (issue #13).

    uv run python -m worker.importar_garmin <caminho> --atleta "<nome>" [--com-clima]

Por padrao nao abre conexao de rede (issue #132). So com `--com-clima` busca o clima no Open-Meteo, das atividades que
entraram ou mudaram; sem a opcao, rode depois `python -m worker.preencher_clima`.

Idempotente: a chave de `atividade` e (atleta_id, fonte, fonte_id) (ADR 0001), mais a regra dos 60 s da ADR 0006.
A gravacao mora na API (`app.ingestao.importacao`); aqui fica so a linha de comando. Os nomes abaixo continuam
exportados daqui para quem ja importava deste modulo.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.ingestao.importacao import (  # noqa: F401
    RelatorioImportacao,
    fuso_min,
    importar,
    normalizar_intensidade,
    pace_s_km,
)

__all__ = ["RelatorioImportacao", "fuso_min", "importar", "main", "normalizar_intensidade", "pace_s_km"]


def clima_do_que_mudou(rel: RelatorioImportacao, cliente=None, session_factory=None) -> None:
    """Clima so das atividades que entraram ou mudaram (ADR 0007, item 7). Erro aqui nunca derruba a importacao."""
    if not rel.ids_alterados:
        return
    try:
        from app.clima import ClienteOpenMeteo
        from app.db.session import SessionLocal
        from app.servicos.clima import preencher_clima

        with (session_factory or SessionLocal)() as session:
            r = preencher_clima(session, cliente or ClienteOpenMeteo(), atividade_ids=rel.ids_alterados)
        print(f"clima: chamadas={r.chamadas}" + (" (rodada parada)" if r.parou else ""))
    except Exception as e:  # noqa: BLE001
        print(f"aviso: clima nao preenchido ({e.__class__.__name__}); rode worker.preencher_clima", file=sys.stderr)


def saude_do_arquivo(caminho: str, atleta: str, session_factory=None) -> None:
    """Limiar e zonas de FC, no fim (ADR 0010, item 3). Sem rede. Erro vira aviso e nunca derruba a importacao."""
    try:
        from app.db.session import SessionLocal
        from app.ingestao.saude import importar_saude

        from worker.importar_saude import imprimir

        with (session_factory or SessionLocal)() as session:
            imprimir(importar_saude(session, caminho, atleta))
    except Exception as e:  # noqa: BLE001
        print(f"aviso: dados de saude nao importados ({e.__class__.__name__}); rode worker.importar_saude",
              file=sys.stderr)


def main(argv: list[str] | None = None, cliente=None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.importar_garmin",
                                description="Importa a exportacao Garmin (zip, pasta, JSON ou FIT) no banco.")
    p.add_argument("caminho")
    p.add_argument("--atleta", required=True, help="nome do atleta (criado se nao existir)")
    p.add_argument("--com-clima", action="store_true",
                   help="busca o clima no Open-Meteo (usa a rede e envia posicoes arredondadas) so das atividades "
                        "que entraram ou mudaram; sem a opcao, nenhuma conexao de rede e aberta")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        rel = importar(session, args.caminho, args.atleta)
    print(f"inseridas={rel.inseridas} atualizadas={rel.atualizadas} ignoradas={rel.ignoradas} "
          f"avisos={len(rel.avisos)}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    saude_do_arquivo(args.caminho, args.atleta)
    if args.com_clima:
        clima_do_que_mudou(rel, cliente=cliente)
    else:
        print("clima: nao buscado (sem rede). Para buscar: uv run python -m worker.preencher_clima")
    return 0


if __name__ == "__main__":
    sys.exit(main())
