"""Serie diaria de carga: CTL, ATL e TSB (issue #142; ADR 0010, itens 5 a 7)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from app.db.models import Atleta
from app.db.session import get_session
from app.metricas import carga as cg
from app.metricas.serie_carga import MOTIVOS
from app.rotas.evolucao import Erro, Periodo, _periodo_valido
from app.servicos.carga_leitura import serie_do_atleta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}", tags=["carga"])

Motivo = Literal["sem_dados_saude", "sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga"]
assert set(Motivo.__args__) == set(MOTIVOS)  # type: ignore[attr-defined]


class DiaCargaOut(BaseModel):
    data: date  # dia local (ADR 0003)
    carga: float  # soma das cargas calculadas do dia (0 em dia sem treino); sem arredondar
    ctl: float  # condicionamento, fim do dia; sem arredondar
    atl: float  # fadiga, fim do dia
    tsb: float  # forma = ctl - atl, do mesmo dia
    aprendendo: bool  # menos de 42 dias desde o primeiro dia da serie: a tela avisa
    atividades: int  # elegiveis do dia
    calculadas: int
    sem_carga: int  # > 0: nao e dia de descanso, houve treino sem dado


class TotaisCargaOut(BaseModel):
    """Contam todas as atividades do atleta, nao so as do periodo pedido."""

    atividades_importadas: int  # calculadas + sem_carga_total + pendentes + ignoradas_multiesporte
    calculadas: int
    sem_carga_total: int
    por_motivo: dict[Motivo, int]  # os seis motivos, sempre todos presentes
    ignoradas_multiesporte: int  # multiesporte_pai e troca: nao contam como sem carga
    pendentes: int  # sem linha ou com linha de versao antiga: o comando `calcular_carga` precisa rodar; ficam fora da serie


class CargaSerieOut(BaseModel):
    atleta_id: int
    versao: str  # serie_carga@1
    versao_carga: str  # carga@1, a da carga por atividade
    periodo: Periodo | None  # o filtro pedido (so recorta `dias`; CTL e ATL sempre partem do primeiro dia com carga)
    aviso: Literal["sem_carga_calculada"] | None  # a serie esta vazia porque nenhuma atividade tem carga calculada
    dias: list[DiaCargaOut]
    totais: TotaisCargaOut


@router.get(
    "/carga",
    response_model=CargaSerieOut,
    operation_id="cargaDoAtleta",
    responses={404: {"model": Erro, "description": "Atleta não encontrado"}},
)
def carga_do_atleta(
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    session: Session = Depends(get_session),
) -> CargaSerieOut:
    """Série diária do primeiro dia com carga até o dia da última atividade, calculada na leitura sobre a carga gravada
    pelo comando `calcular_carga`. `inicio` e `fim` (AAAA-MM-DD, datas locais, inclusivas) só recortam `dias`."""
    _periodo_valido(inicio, fim)
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")
    lida = serie_do_atleta(session, atleta_id)
    s, t = lida.serie, lida.serie.totais
    dias = [d for d in s.dias if (inicio is None or d.dia >= inicio) and (fim is None or d.dia <= fim)]
    return CargaSerieOut(
        atleta_id=atleta_id,
        versao=s.versao,
        versao_carga=cg.VERSAO,
        periodo=Periodo(inicio=inicio, fim=fim) if (inicio or fim) else None,
        aviso="sem_carga_calculada" if not s.dias else None,
        dias=[DiaCargaOut(data=d.dia, carga=d.carga, ctl=d.ctl, atl=d.atl, tsb=d.tsb, aprendendo=d.aprendendo,
                          atividades=d.atividades, calculadas=d.calculadas, sem_carga=d.sem_carga) for d in dias],
        totais=TotaisCargaOut(
            atividades_importadas=lida.atividades_importadas, calculadas=t.calculadas, sem_carga_total=t.sem_carga_total,
            por_motivo=t.por_motivo, ignoradas_multiesporte=t.ignoradas_multiesporte, pendentes=lida.pendentes,
        ),
    )
