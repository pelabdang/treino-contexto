"""Upload de arquivo FIT (issue #95, ADR 0006, itens 4 e 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.db.models import Atleta
from app.db.session import get_session
from app.ingestao.fit_guardado import AtletaInexistente
from app.ingestao.importacao import (
    TAMANHO_MAX_FIT,
    FitGrande,
    FitInvalido,
    FitNaoEAtividade,
    importar_fit,
)
from app.rotas.evolucao import Erro
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}/atividades", tags=["atividades"])

PEDACO = 64 * 1024


class UploadFitOut(BaseModel):
    resultado: Literal["inserida", "atualizada", "ignorada"]
    atividade_id: int
    avisos: list[str]


def get_fit_dir() -> Path | None:
    """Pasta dos FIT guardados; `None` = `FIT_DIR` da configuração. Os testes trocam por um diretório temporário."""
    return None


def _ler_limitado(arquivo: UploadFile) -> bytes:
    """Lê em pedaços e para em 10 MB + 1: o limite vale pelos bytes realmente lidos, não pelo Content-Length."""
    partes: list[bytes] = []
    total = 0
    while True:
        parte = arquivo.file.read(PEDACO)
        if not parte:
            return b"".join(partes)
        total += len(parte)
        if total > TAMANHO_MAX_FIT:
            raise HTTPException(status_code=413, detail="arquivo acima de 10 MB")
        partes.append(parte)


@router.post(
    "/fit",
    status_code=201,
    response_model=UploadFitOut,
    operation_id="enviarAtividadeFit",
    responses={
        200: {"model": UploadFitOut, "description": "Atividade que já existia (atualizada ou ignorada)"},
        201: {"model": UploadFitOut, "description": "Atividade inserida"},
        400: {"model": Erro, "description": "FIT inválido ou que não é uma atividade, ou extensão diferente de .fit"},
        404: {"model": Erro, "description": "Atleta não encontrado"},
        413: {"model": Erro, "description": "Arquivo acima de 10 MB"},
    },
)
def enviar_atividade_fit(
    atleta_id: int,
    response: Response,
    arquivo: UploadFile = File(..., description="Arquivo .fit de uma atividade (até 10 MB)"),
    session: Session = Depends(get_session),
    fit_dir: Path | None = Depends(get_fit_dir),
) -> UploadFitOut:
    """Envia um FIT (campo multipart `arquivo`). `201` se a atividade é nova; `200` se já existia."""
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    if not (arquivo.filename or "").lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="o arquivo precisa ter extensão .fit")
    conteudo = _ler_limitado(arquivo)
    try:
        r = importar_fit(session, atleta_id, conteudo, fit_dir)
    except AtletaInexistente:
        raise HTTPException(status_code=404, detail="atleta não encontrado") from None
    except FitGrande:
        raise HTTPException(status_code=413, detail="arquivo acima de 10 MB") from None
    except FitNaoEAtividade:
        raise HTTPException(status_code=400, detail="o arquivo é um FIT, mas não é uma atividade") from None
    except FitInvalido:
        raise HTTPException(status_code=400, detail="FIT inválido ou corrompido") from None
    if r.resultado != "inserida":
        response.status_code = 200
    return UploadFitOut(resultado=r.resultado, atividade_id=r.atividade_id, avisos=r.avisos)
