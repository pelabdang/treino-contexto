"""Rotas da evolução dos tiros de 1 km (issue #16)."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Atleta
from app.db.session import get_session
from app.metricas.tiros_1km import VERSAO, formatar_pace
from app.servicos.evolucao_tiros import SessaoSerie, sessoes_tiros_1km

router = APIRouter(prefix="/atletas/{atleta_id}/evolucao", tags=["evolução"])


class Unidades(BaseModel):
    pace: str = "s/km"
    fc: str = "bpm"
    distancia: str = "m"
    duracao: str = "s"


class Periodo(BaseModel):
    inicio: date | None
    fim: date | None


class TiroOut(BaseModel):
    ordem: int
    distancia_m: float
    duracao_s: float
    pace_s_km: float | None
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
    metrica: str
    versao_calculo: str
    unidades: Unidades
    periodo: Periodo | None
    sessoes: list[SessaoOut]


def _um_decimal(v: float | None) -> float | None:
    return None if v is None else round(v, 1)


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
        tiros=[
            TiroOut(
                ordem=t.ordem,
                distancia_m=t.distancia_m,
                duracao_s=t.duracao_s,
                pace_s_km=_um_decimal(t.duracao_s / t.distancia_m * 1000) if t.distancia_m > 0 else None,
                fc_media=t.fc_media,
            )
            for t in s.tiros
        ],
    )


def _atleta_ou_404(session: Session, atleta_id: int) -> None:
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")


@router.get("/tiros-1km", response_model=EvolucaoTiros1km)
def evolucao_tiros_1km(
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    session: Session = Depends(get_session),
) -> EvolucaoTiros1km:
    """Pace e FC médios dos tiros de 1 km por sessão. `inicio` e `fim` (AAAA-MM-DD) são datas locais, inclusivas."""
    _atleta_ou_404(session, atleta_id)
    sessoes = sessoes_tiros_1km(session, atleta_id, inicio, fim)
    return EvolucaoTiros1km(
        atleta_id=atleta_id,
        metrica="tiros_1km",
        versao_calculo=sessoes[0].ponto.versao if sessoes else VERSAO,
        unidades=Unidades(),
        periodo=Periodo(inicio=inicio, fim=fim) if (inicio or fim) else None,
        sessoes=[_sessao_out(s) for s in sessoes],
    )
