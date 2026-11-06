"""Upload de arquivo FIT (issue #95, ADR 0006, itens 4 e 5)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from app.db.models import Atividade, Atleta
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
from app.metricas.tiros_1km import formatar_pace
from app.servicos.fuso import inicio_local
from app.servicos.clima import ClimaDaAtividade, EstadoClima, clima_da_atividade
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}/atividades", tags=["atividades"])

PEDACO = 64 * 1024


class UploadFitOut(BaseModel):
    resultado: Literal["inserida", "atualizada", "ignorada"]
    atividade_id: int
    avisos: list[str]


class ClimaOut(BaseModel):
    """Clima da atividade (ADR 0007, item 5). Os quatro valores so existem em `ok`; nos outros estados nem aparecem."""

    estado: EstadoClima
    temperatura_c: float | None = Field(None, exclude_if=lambda v: v is None)
    sensacao_c: float | None = Field(None, exclude_if=lambda v: v is None)
    umidade_pct: float | None = Field(None, exclude_if=lambda v: v is None)
    vento_kmh: float | None = Field(None, exclude_if=lambda v: v is None)
    atribuicao: str | None = Field(None, exclude_if=lambda v: v is None)  # so em `ok` (ADR 0007, item 4)


class AtividadeOut(BaseModel):
    """A atividade como a API mostra. A posicao de inicio nunca sai (ADR 0007)."""

    atividade_id: int
    modalidade: str
    subtipo: str | None
    inicio: datetime  # UTC
    duracao_s: float
    distancia_m: float | None
    fc_media: float | None
    clima: ClimaOut | None = None  # campo novo e opcional
    # Campos prontos para a tela (#158): a API formata, o app mostra (ADR 0004, adendo 2).
    data_local: str  # AAAA-MM-DD, pelo fuso da atividade (ADR 0003)
    hora_local: str  # HH:MM, pelo fuso da atividade
    duracao: str  # h:mm:ss (horas sem limite, segundos arredondados com meio para cima)
    pace_medio: str | None = None  # m:ss por km; so corrida com distancia (formatar_pace)


ATRIBUICAO_CLIMA = "Weather data by Open-Meteo.com"
MODALIDADES_COM_PACE = ("corrida",)


def _duracao_hms(duracao_s: float) -> str:
    total = int(duracao_s + 0.5)
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _pace_medio(a: Atividade) -> str | None:
    if a.modalidade not in MODALIDADES_COM_PACE or not a.distancia_m or a.distancia_m <= 0 or a.duracao_s <= 0:
        return None
    return formatar_pace(a.duracao_s / (a.distancia_m / 1000))


def _clima_out(c: ClimaDaAtividade) -> ClimaOut:
    return ClimaOut(
        estado=c.estado,
        temperatura_c=c.temperatura_c,
        sensacao_c=c.sensacao_c,
        umidade_pct=c.umidade_pct,
        vento_kmh=c.vento_kmh,
        atribuicao=ATRIBUICAO_CLIMA if c.estado == "ok" else None,
    )


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


@router.get(
    "/{atividade_id}",
    response_model=AtividadeOut,
    operation_id="buscarAtividade",
    responses={404: {"model": Erro, "description": "Atleta ou atividade não encontrados (atividade de outro atleta também)"}},
)
def buscar_atividade(
    atleta_id: int,
    atividade_id: int,
    session: Session = Depends(get_session),
) -> AtividadeOut:
    """A atividade com o `clima` (ADR 0007). `indoor`, `sem_posicao`, `pendente` e `falha` dizem por que não há valores."""
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    a = session.get(Atividade, atividade_id)
    if a is None or a.atleta_id != atleta_id:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    clima = clima_da_atividade(session, atividade_id)
    local = inicio_local(a.inicio, a.fuso_min)
    return AtividadeOut(
        atividade_id=a.id,
        modalidade=a.modalidade,
        subtipo=a.subtipo,
        inicio=a.inicio,
        duracao_s=a.duracao_s,
        distancia_m=a.distancia_m,
        fc_media=a.fc_media,
        clima=None if clima is None else _clima_out(clima),
        data_local=local.date().isoformat(),
        hora_local=local.strftime("%H:%M"),
        duracao=_duracao_hms(a.duracao_s),
        pace_medio=_pace_medio(a),
    )
