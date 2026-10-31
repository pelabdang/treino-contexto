"""Entrada do parser: zip, pasta, summarizedActivities.json ou .fit soltos."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from . import tipos, unidades
from .fit import FitLido, ler_fit
from .modelos import AtividadeImportada

log = logging.getLogger(__name__)

TOLERANCIA_S = 60
SUFIXO_JSON = "summarizedactivities.json"
PROFUNDIDADE_MAX_ZIP = 3


@dataclass
class _Fit:
    caminho: str
    lido: FitLido
    usado: bool = False


def _arquivos(caminho: Path) -> Iterator[tuple[str, bytes]]:
    """Gera (caminho logico, bytes) de todo arquivo relevante, abrindo zips aninhados."""
    if caminho.is_dir():
        for f in sorted(p for p in caminho.rglob("*") if p.is_file()):
            yield from _conteudo(f.relative_to(caminho).as_posix(), f.read_bytes(), 0)
    elif caminho.is_file():
        yield from _conteudo(caminho.name, caminho.read_bytes(), 0, solto=True)
    else:
        raise FileNotFoundError(f"Exportacao nao encontrada: {caminho}")


def _conteudo(nome: str, dados: bytes, nivel: int, solto: bool = False) -> Iterator[tuple[str, bytes]]:
    baixo = nome.lower()
    if baixo.endswith(".zip"):
        if nivel >= PROFUNDIDADE_MAX_ZIP:
            log.warning("zip aninhado fundo demais, ignorado: %s", nome)
            return
        try:
            with zipfile.ZipFile(io.BytesIO(dados)) as z:
                for membro in sorted(z.namelist()):
                    if not membro.endswith("/"):
                        yield from _conteudo(f"{nome}!/{membro}", z.read(membro), nivel + 1)
        except zipfile.BadZipFile:
            log.warning("zip corrompido, ignorado: %s", nome)
    elif baixo.endswith(".fit"):
        yield nome, dados
    elif baixo.endswith(".json") and (solto or baixo.endswith(SUFIXO_JSON)):
        yield nome, dados


def _atividades_json(nome: str, dados: bytes) -> list[dict]:
    try:
        obj = json.loads(dados)
    except ValueError:
        log.warning("JSON invalido, ignorado: %s", nome)
        return []
    itens: list[dict] = []
    blocos = obj if isinstance(obj, list) else [obj]
    for b in blocos:
        if isinstance(b, dict) and "summarizedActivitiesExport" in b:
            itens.extend(b["summarizedActivitiesExport"])
        elif isinstance(b, dict) and "activityId" in b:
            itens.append(b)
    return [i for i in itens if isinstance(i, dict)]


def _de_json(item: dict, caminho_json: str) -> AtividadeImportada | None:
    try:
        fonte_id = str(item["activityId"])
        inicio = unidades.epoch_ms_para_datetime(item["startTimeGmt"])
    except (KeyError, TypeError, ValueError, OverflowError):
        log.warning("atividade do JSON sem activityId/startTimeGmt validos, ignorada (%s)", caminho_json)
        return None
    modalidade, subtipo = tipos.de_json(item.get("activityType"), item.get("sportType"))

    def conv(chave, f):
        v = item.get(chave)
        return f(v) if isinstance(v, (int, float)) else None

    hr = item.get("avgHr")
    local = item.get("startTimeLocal")
    gmt = item["startTimeGmt"]
    inicio_local = (unidades.inicio_local(gmt, local)
                    if isinstance(local, (int, float)) and -12 * 3600_000 <= local - gmt <= 14 * 3600_000 else None)
    return AtividadeImportada(
        fonte_id=fonte_id, modalidade=modalidade, subtipo=subtipo, inicio=inicio,
        inicio_local=inicio_local, duracao_s=conv("duration", unidades.ms_para_s), distancia_m=conv("distance", unidades.cm_para_m),
        fc_media=round(hr) if isinstance(hr, (int, float)) else None, arquivo_bruto=caminho_json,
    )


def _de_fit(f: _Fit) -> AtividadeImportada:
    modalidade, subtipo = tipos.de_fit(f.lido.sport, f.lido.sub_sport)
    return AtividadeImportada(
        fonte_id=f.lido.id_derivado, modalidade=modalidade, subtipo=subtipo, inicio=f.lido.inicio,
        duracao_s=f.lido.duracao_s, distancia_m=f.lido.distancia_m, fc_media=f.lido.fc_media,
        arquivo_bruto=f.caminho, voltas=list(f.lido.voltas),
    )


def ler_exportacao(caminho: str | Path) -> list[AtividadeImportada]:
    """Le a exportacao Garmin (zip, pasta, summarizedActivities.json ou .fit) sem tocar no banco.

    Arquivo corrompido ou atividade sem FIT nao derruba a leitura: entra sem voltas e gera aviso no log.
    """
    jsons: dict[str, AtividadeImportada] = {}
    fits: list[_Fit] = []
    for nome, dados in _arquivos(Path(caminho)):
        if nome.lower().endswith(".fit"):
            try:
                lido = ler_fit(dados)
                if any(f.lido.id_derivado == lido.id_derivado for f in fits):
                    log.warning("FIT repetido na exportacao, ignorado: %s", nome)
                    continue
                fits.append(_Fit(nome, lido))
            except ValueError as e:
                log.warning("FIT ignorado (%s): %s", nome, e)
        else:
            for item in _atividades_json(nome, dados):
                ativ = _de_json(item, nome)
                if ativ and ativ.fonte_id not in jsons:
                    jsons[ativ.fonte_id] = ativ

    for ativ in sorted(jsons.values(), key=lambda a: (a.inicio, a.fonte_id)):
        candidatos = [f for f in fits if not f.usado
                      and abs((f.lido.inicio - ativ.inicio).total_seconds()) <= TOLERANCIA_S]
        if not candidatos:
            log.warning("atividade %s sem FIT correspondente: entra sem voltas", ativ.fonte_id)
            continue
        f = min(candidatos, key=lambda f: abs((f.lido.inicio - ativ.inicio).total_seconds()))
        f.usado = True
        ativ.voltas = list(f.lido.voltas)
        ativ.arquivo_bruto = f.caminho

    resultado = list(jsons.values()) + [_de_fit(f) for f in fits if not f.usado]
    return sorted(resultado, key=lambda a: (a.inicio, a.fonte_id))
