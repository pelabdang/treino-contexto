"""Confere a nossa carga com a carga aguda/crônica do Garmin, só descritivo (issue #144; ADR 0010, item 8).

    uv run python -m worker.conferir_carga --atleta-id <id> [--saida <pasta>]

Só lê o banco (``carga_atividade`` e ``carga_garmin_dia``); sem rede. Grava em ``entregas/meta-6/`` (fora do git):
  conferencia-carga-atleta-<id>.csv          dia a dia, as duas séries e se o dia entrou na comparação
  conferencia-carga-atleta-<id>-resumo.csv   Spearman por medida (níveis, diferenças, defasagem -3..+3, razão) e n
  conferencia-carga-atleta-<id>-cobertura.csv  dias de cada série, em comum, descartados e comparados
Não há faixa de aprovação. O stdout leva só contagens (os valores do atleta ficam nos arquivos).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from app.db.models import Atleta
from app.metricas.conferencia_carga import Conferencia, DiaGarmin, razao_nossa
from app.metricas.serie_carga import DiaCarga
from app.servicos.conferencia_carga import conferencia_do_atleta
from sqlalchemy.orm import Session

PASTA_PADRAO = Path("entregas") / "meta-6"
COLUNAS_DIA = ("dia", "nossa_carga", "nossa_ctl", "nossa_atl", "nossa_tsb", "nossa_razao_atl_ctl", "atividades_sem_carga",
               "garmin_aguda", "garmin_cronica", "garmin_razao", "entrou_na_comparacao")
COLUNAS_RESUMO = ("regra", "grupo", "comparacao", "defasagem_dias", "n_pares", "spearman")
COLUNAS_COBERTURA = ("regra", "dias_nossa", "dias_garmin", "dias_em_comum", "descartados_sem_carga", "dias_comparados")


class AtletaInexistente(LookupError):
    pass


def _f(x: float | None) -> str:
    return "" if x is None else f"{x:.6f}"


def linhas_dia(nossa: Sequence[DiaCarga], garmin: Sequence[DiaGarmin]) -> list[dict[str, str]]:
    """Uma linha por dia presente em alguma das séries; ``entrou_na_comparacao`` pela regra da ADR."""
    dn, dg = {d.dia: d for d in nossa}, {g.dia: g for g in garmin}
    saida = []
    for dia in sorted(set(dn) | set(dg)):
        n, g = dn.get(dia), dg.get(dia)
        if n is None or g is None:
            entrou = "nao_so_garmin" if n is None else "nao_so_nossa"
        else:
            entrou = "nao_atividade_sem_carga" if n.sem_carga > 0 else "sim"
        saida.append({
            "dia": dia.isoformat(),
            "nossa_carga": _f(n.carga) if n else "", "nossa_ctl": _f(n.ctl) if n else "",
            "nossa_atl": _f(n.atl) if n else "", "nossa_tsb": _f(n.tsb) if n else "",
            "nossa_razao_atl_ctl": _f(razao_nossa(n)) if n else "",
            "atividades_sem_carga": str(n.sem_carga) if n else "",
            "garmin_aguda": _f(g.aguda) if g else "", "garmin_cronica": _f(g.cronica) if g else "",
            "garmin_razao": _f(g.razao) if g else "", "entrou_na_comparacao": entrou,
        })
    return saida


def linhas_resumo(conferencias: dict[str, Conferencia]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    resumo, cobertura = [], []
    for regra, c in conferencias.items():
        for m in c.medidas:
            resumo.append({"regra": regra, "grupo": m.grupo, "comparacao": m.comparacao, "defasagem_dias": str(m.defasagem),
                           "n_pares": str(m.n), "spearman": _f(m.spearman)})
        k = c.cobertura
        cobertura.append({"regra": regra, "dias_nossa": str(k.dias_nossa), "dias_garmin": str(k.dias_garmin),
                          "dias_em_comum": str(k.dias_em_comum), "descartados_sem_carga": str(k.descartados_sem_carga),
                          "dias_comparados": str(k.dias_comparados)})
    return resumo, cobertura


def _gravar(caminho: Path, colunas: Sequence[str], linhas: list[dict[str, str]]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def conferir(session: Session, atleta_id: int, pasta: Path = PASTA_PADRAO) -> tuple[list[Path], Conferencia, int]:
    """Grava os três CSVs e devolve os caminhos, a conferência da regra da ADR e as atividades sem linha de carga."""
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    r = conferencia_do_atleta(session, atleta_id)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"conferencia-carga-atleta-{atleta_id}"
    resumo, cobertura = linhas_resumo({"adr": r.conferencia, "todos_os_dias": r.complementar})
    caminhos = [Path(f"{base}.csv"), Path(f"{base}-resumo.csv"), Path(f"{base}-cobertura.csv")]
    _gravar(caminhos[0], COLUNAS_DIA, linhas_dia(r.nossa, r.garmin))
    _gravar(caminhos[1], COLUNAS_RESUMO, resumo)
    _gravar(caminhos[2], COLUNAS_COBERTURA, cobertura)
    return caminhos, r.conferencia, r.sem_linha


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.conferir_carga",
                                description="Confere a nossa carga com a do Garmin (descritivo, sem rede).")
    p.add_argument("--atleta-id", type=int, required=True)
    p.add_argument("--saida", type=Path, default=PASTA_PADRAO, help="pasta de saída (padrão: entregas/meta-6)")
    args = p.parse_args(argv)

    from app.db.session import SessionLocal  # usa DATABASE_URL

    try:
        with SessionLocal() as session:
            caminhos, c, sem_linha = conferir(session, args.atleta_id, args.saida)
    except AtletaInexistente as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    if sem_linha:
        print(f"aviso: {sem_linha} atividade(s) sem carga gravada; rode worker.calcular_carga", file=sys.stderr)
    k = c.cobertura
    print(f"conferência {c.versao}: dias comparados {k.dias_comparados} de {k.dias_em_comum} em comum "
          f"(descartados por atividade sem carga: {k.descartados_sem_carga})")
    for caminho in caminhos:
        print(f"gravado: {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
