"""Rotas da evolução dos tiros de 1 km (issue #16)."""

from __future__ import annotations

from datetime import date, datetime

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Atleta
from app.graficos.tiros_1km import render_png
from app.db.session import get_session
from app.metricas.tiros_1km import VERSAO, formatar_pace
from app.servicos.evolucao_tiros import SessaoSerie, reclassificacao_pendente, sessoes_tiros_1km

router = APIRouter(prefix="/atletas/{atleta_id}/evolucao", tags=["evolução"])


class Erro(BaseModel):
    detail: str


class Unidades(BaseModel):
    pace: str
    fc: str
    distancia: str
    duracao: str


class Periodo(BaseModel):
    inicio: date | None
    fim: date | None


class TiroOut(BaseModel):
    ordem: int
    distancia_m: float | None  # null quando o segmento não tem distância
    duracao_s: float
    pace_s_km: float | None
    pace: str | None  # m:ss, de pace_s_km sem arredondar; null se pace_s_km é null
    fc_media: float | None


class SessaoOut(BaseModel):
    atividade_id: int
    data: date  # data local (ADR 0003)
    inicio: datetime  # UTC
    n_tiros: int
    pace_medio_s_km: float
    pace_medio: str  # m:ss
    fc_media: float | None
    tiros: list[TiroOut]


class EvolucaoTiros1km(BaseModel):
    atleta_id: int
    metrica: Literal["tiros_1km"]
    versao_calculo: str  # sempre a VERSAO da regra atual
    reclassificacao_pendente: bool  # há segmento gravado com outra versao_deteccao
    unidades: Unidades
    periodo: Periodo | None
    sessoes: list[SessaoOut]


def _um_decimal(v: float | None) -> float | None:
    return None if v is None else round(v, 1)


def _tiro_out(t) -> TiroOut:
    pace = t.duracao_s / t.distancia_m * 1000 if t.distancia_m else None
    return TiroOut(
        ordem=t.ordem,
        distancia_m=_um_decimal(t.distancia_m),
        duracao_s=_um_decimal(t.duracao_s),
        pace_s_km=_um_decimal(pace),
        pace=None if pace is None else formatar_pace(pace),
        fc_media=_um_decimal(t.fc_media),
    )


def _sessao_out(s: SessaoSerie) -> SessaoOut:
    p = s.ponto
    return SessaoOut(
        atividade_id=p.atividade_id,
        data=p.data,
        inicio=s.inicio,
        n_tiros=p.n_tiros,
        pace_medio_s_km=_um_decimal(p.pace_s_km),
        pace_medio=formatar_pace(p.pace_s_km),
        fc_media=_um_decimal(p.fc_media),
        tiros=[_tiro_out(t) for t in s.tiros],
    )


def _atleta_ou_404(session: Session, atleta_id: int) -> Atleta:
    atleta = session.get(Atleta, atleta_id)
    if atleta is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    return atleta


def _periodo_valido(inicio: date | None, fim: date | None) -> None:
    """`inicio` depois de `fim` é 422, no formato de erro do FastAPI (`detail` é lista)."""
    if inicio and fim and inicio > fim:
        raise RequestValidationError([{
            "type": "value_error",
            "loc": ("query", "fim"),
            "msg": "fim deve ser igual ou posterior a inicio",
            "input": fim.isoformat(),
        }])


_ERRO_404 = {404: {"model": Erro, "description": "Atleta não encontrado"}}


@router.get("/tiros-1km", response_model=EvolucaoTiros1km, operation_id="evolucaoTiros1km", responses=_ERRO_404)
def evolucao_tiros_1km(
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    session: Session = Depends(get_session),
) -> EvolucaoTiros1km:
    """Pace e FC médios dos tiros de 1 km por sessão. `inicio` e `fim` (AAAA-MM-DD) são datas locais, inclusivas."""
    _periodo_valido(inicio, fim)
    _atleta_ou_404(session, atleta_id)
    sessoes = sessoes_tiros_1km(session, atleta_id, inicio, fim)
    return EvolucaoTiros1km(
        atleta_id=atleta_id,
        metrica="tiros_1km",
        versao_calculo=VERSAO,
        reclassificacao_pendente=reclassificacao_pendente(session, atleta_id, inicio, fim),
        unidades=Unidades(pace="s/km", fc="bpm", distancia="m", duracao="s"),
        periodo=Periodo(inicio=inicio, fim=fim) if (inicio or fim) else None,
        sessoes=[_sessao_out(s) for s in sessoes],
    )


@router.get(
    "/tiros-1km.png",
    response_class=Response,
    operation_id="evolucaoTiros1kmPng",
    responses={200: {"content": {"image/png": {}}, "description": "Gráfico PNG (1600 x 1000)"}, **_ERRO_404},
)
def evolucao_tiros_1km_png(
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    session: Session = Depends(get_session),
) -> Response:
    """O mesmo gráfico do comando de `entregas/`, com os mesmos filtros do JSON."""
    _periodo_valido(inicio, fim)
    atleta = _atleta_ou_404(session, atleta_id)
    serie = [s.ponto for s in sessoes_tiros_1km(session, atleta_id, inicio, fim)]
    return Response(content=render_png(serie, atleta.nome), media_type="image/png")
