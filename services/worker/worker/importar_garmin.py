"""Importa a exportacao Garmin para o banco (issue #13).

    uv run python -m worker.importar_garmin <caminho> --atleta "<nome>"

Idempotente: a chave de `atividade` e (atleta_id, fonte, fonte_id) (ADR 0001).
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.db.models import INTENSIDADES, Atividade, Atleta, Segmento
from app.servicos.evolucao_tiros import classificar_atividades
from sqlalchemy import select
from sqlalchemy.orm import Session

from worker.garmin import AtividadeImportada, VoltaImportada, ler_exportacao
from worker.garmin.unidades import para_utc

log = logging.getLogger(__name__)


@dataclass
class RelatorioImportacao:
    inseridas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0  # ja estavam iguais no banco
    avisos: list[str] = field(default_factory=list)


class _ColetaAvisos(logging.Handler):
    """Junta os avisos do parser no relatorio."""

    def __init__(self, destino: list[str]):
        super().__init__(logging.WARNING)
        self.destino = destino

    def emit(self, record: logging.LogRecord) -> None:
        self.destino.append(record.getMessage())


def normalizar_intensidade(valor: str | None) -> str | None:
    """Minusculas e sem espacos; valor fora da lista do CHECK vira "other"; ausente fica None."""
    if valor is None:
        return None
    v = str(valor).strip().lower()
    return v if v in INTENSIDADES else "other"


def pace_s_km(duracao_s: float, distancia_m: float | None) -> float | None:
    if not distancia_m or distancia_m <= 0:
        return None
    return duracao_s / distancia_m * 1000


def _chave_volta(ordem, offset, dur, dist, fc, intens) -> tuple:
    return (ordem, offset, dur, dist, fc, intens)


def _voltas_novas(voltas: list[VoltaImportada]) -> list[tuple]:
    return [_chave_volta(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media,
                         normalizar_intensidade(v.intensidade)) for v in voltas]


def _voltas_no_banco(ativ: Atividade) -> list[tuple]:
    return [_chave_volta(s.ordem, s.inicio_offset_s, s.duracao_s, s.distancia_m, s.fc_media, s.intensidade)
            for s in ativ.segmentos]  # todos os tipos: a classificacao (#14) troca volta por tiro/recuperacao


def _campos(a: AtividadeImportada, duracao_s: float) -> dict:
    campos = dict(modalidade=a.modalidade, subtipo=a.subtipo, inicio=para_utc(a.inicio), duracao_s=duracao_s,
                  distancia_m=a.distancia_m, fc_media=a.fc_media, arquivo_bruto=a.arquivo_bruto)
    fuso = fuso_min(a)
    if fuso is not None:  # sem horario local na fonte nao apaga um fuso ja gravado (ADR 0003)
        campos["fuso_min"] = fuso
    return campos


def fuso_min(a: AtividadeImportada) -> int | None:
    """Deslocamento do fuso em minutos (inicio_local - inicio); None se a fonte nao traz o horario local."""
    if a.inicio_local is None or a.inicio_local.utcoffset() is None:
        return None
    return round(a.inicio_local.utcoffset().total_seconds() / 60)


def _segmentos(voltas: list[VoltaImportada]) -> list[Segmento]:
    return [Segmento(ordem=v.ordem, tipo="volta", inicio_offset_s=v.inicio_offset_s, duracao_s=v.duracao_s,
                     distancia_m=v.distancia_m, fc_media=v.fc_media,
                     pace_s_km=pace_s_km(v.duracao_s, v.distancia_m),
                     intensidade=normalizar_intensidade(v.intensidade)) for v in voltas]


def _igual(ativ: Atividade, campos: dict) -> bool:
    return all(
        (para_utc(getattr(ativ, k)) == v) if k == "inicio" else getattr(ativ, k) == v
        for k, v in campos.items()
        if k != "arquivo_bruto"  # o caminho muda conforme o formato da entrada; nao conta como mudanca
    )


def importar(session: Session, caminho: str | Path, atleta_nome: str) -> RelatorioImportacao:
    """Le a exportacao e grava atividades e voltas. Reimportar nao duplica nada.

    Atividade ja existente: se nada mudou, e ignorada (segmentos e classificacoes da #14 ficam intactos);
    se mudou, os campos sao atualizados e, se as voltas mudaram, os segmentos sao substituidos
    (o `id` da atividade nao muda). No fim, classifica as corridas do atleta. Uma leitura sem voltas nunca apaga as voltas ja gravadas.
    """
    rel = RelatorioImportacao()
    coleta = _ColetaAvisos(rel.avisos)
    logger_parser = logging.getLogger("worker.garmin")
    logger_parser.addHandler(coleta)
    try:
        importadas = ler_exportacao(caminho)
    finally:
        logger_parser.removeHandler(coleta)

    atleta = session.scalars(select(Atleta).where(Atleta.nome == atleta_nome).order_by(Atleta.id)).first()
    if atleta is None:
        atleta = Atleta(nome=atleta_nome)
        session.add(atleta)
        session.flush()

    for a in importadas:
        duracao = a.duracao_s if a.duracao_s is not None else (
            sum(v.duracao_s for v in a.voltas) or None)
        if duracao is None:
            rel.avisos.append(f"atividade {a.fonte_id} sem duracao, ignorada")
            continue
        campos = _campos(a, duracao)
        ativ = session.scalars(select(Atividade).where(
            Atividade.atleta_id == atleta.id, Atividade.fonte == a.fonte, Atividade.fonte_id == a.fonte_id,
        )).first()
        if ativ is None:
            session.add(Atividade(atleta_id=atleta.id, fonte=a.fonte, fonte_id=a.fonte_id,
                                  segmentos=_segmentos(a.voltas), **campos))
            rel.inseridas += 1
            continue

        mudou_campos = not _igual(ativ, campos)
        mudou_voltas = bool(a.voltas) and _voltas_novas(a.voltas) != _voltas_no_banco(ativ)
        if not a.voltas and ativ.segmentos:
            rel.avisos.append(f"atividade {a.fonte_id} veio sem voltas; mantidas as {len(ativ.segmentos)} gravadas")
        if not (mudou_campos or mudou_voltas):
            rel.ignoradas += 1
            continue
        if mudou_campos:
            for k, v in campos.items():
                setattr(ativ, k, v)
        if mudou_voltas:
            ativ.segmentos.clear()
            session.flush()  # remove os antigos antes de inserir (unique atividade_id + ordem)
            ativ.segmentos.extend(_segmentos(a.voltas))
        rel.atualizadas += 1

    session.commit()
    classificar_atividades(session, atleta.id)  # tiros/recuperacoes e tipo do treino (#14); idempotente
    return rel


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.importar_garmin",
                                description="Importa a exportacao Garmin (zip, pasta, JSON ou FIT) no banco.")
    p.add_argument("caminho")
    p.add_argument("--atleta", required=True, help="nome do atleta (criado se nao existir)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    from app.db.session import SessionLocal  # usa DATABASE_URL

    with SessionLocal() as session:
        rel = importar(session, args.caminho, args.atleta)
    print(f"inseridas={rel.inseridas} atualizadas={rel.atualizadas} ignoradas={rel.ignoradas} "
          f"avisos={len(rel.avisos)}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
