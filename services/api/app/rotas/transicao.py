"""Treino de transicao pela API: listar, comparar e corrigir o rotulo (issue #170, ADR 0009, item 5)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from app.db.models import Atividade, Atleta, RotuloTransicao
from app.db.session import get_session
from app.metricas.tiros_1km import formatar_pace
from app.rotas.evolucao import Erro, Periodo, _periodo_valido
from app.servicos.fuso import data_local, inicio_local
from app.servicos.transicao import ORIGEM_ATLETA
from app.servicos.transicao_grupos import Grupo, Parte, grupos_do_atleta, ritmo
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}", tags=["treino de transição"])

_404_ATLETA = {404: {"model": Erro, "description": "Atleta não encontrado"}}


class TransicaoOut(BaseModel):
    """Rotulo "treino de transicao" da atividade. Sem linha no banco e `valor = false`, `origem = null`."""

    valor: bool
    origem: Literal["sugerido", "atleta"] | None = None


class CorrecaoIn(BaseModel):
    transicao: bool


class ParteOut(BaseModel):
    ordem: int
    atividade_id: int
    modalidade: str
    inicio: datetime  # UTC
    hora_local: str  # HH:MM
    duracao_s: float
    duracao: str  # h:mm:ss
    distancia_m: float | None
    distancia: str | None  # "10,00 km"; natacao "1.800 m" (ADR 0004, adendo 3)
    fc_media: float | None
    ritmo_valor: float | None  # corrida s/km, natacao s/100m, ciclismo km/h (1 casa)
    ritmo_unidade: Literal["s/km", "s/100m", "km/h"] | None
    ritmo: str | None  # "4:39 /km", "2:05 /100 m", "25,3 km/h"; null sem distancia


class IntervaloOut(BaseModel):
    """Intervalo ESTIMADO entre duas partes seguidas: `duracao_s` e tempo em movimento, entao o real pode ser menor."""

    de_atividade_id: int
    para_atividade_id: int
    intervalo_estimado_s: float
    intervalo_estimado: str  # m:ss


class GrupoOut(BaseModel):
    grupo_id: int  # derivado: muda quando uma correcao parte ou junta o grupo; o app nao deve guardar
    forma: str  # sequencia de modalidades, ex. "ciclismo>corrida"
    incompleto: bool  # uma parte so (o atleta marcou "sim" numa atividade avulsa)
    inicio: datetime  # UTC, da primeira parte
    fim_estimado: datetime  # UTC, da ultima parte
    data_local: date
    hora_local: str
    partes: list[ParteOut]
    transicoes: list[IntervaloOut]  # len(partes) - 1
    soma_duracoes_s: float
    soma_duracoes: str  # h:mm:ss
    soma_intervalos_estimados_s: float
    soma_intervalos_estimados: str  # m:ss
    tempo_total_s: float  # inicio da primeira ao fim estimado da ultima
    tempo_total: str  # h:mm:ss
    fc_media: float | None  # media das partes ponderada pela duracao, so entre as que tem FC


class TreinosDeTransicaoOut(BaseModel):
    periodo: Periodo | None = Field(None, exclude_if=lambda v: v is None)
    grupos: list[GrupoOut]  # mais recentes primeiro


class DiferencaParteOut(BaseModel):
    """B menos A. Sem nota e sem "melhor"."""

    ordem: int
    modalidade: str
    duracao_dif_s: float
    duracao_dif: str  # "+0:42", "-1:05"
    ritmo_dif: float | None  # na unidade do ritmo; null se alguma parte nao tem distancia
    ritmo_dif_texto: str | None
    fc_dif: float | None
    fc_dif_texto: str | None  # "+3 bpm"


class DiferencaTotalOut(BaseModel):
    soma_duracoes_dif_s: float
    soma_duracoes_dif: str
    soma_intervalos_estimados_dif_s: float  # estimativa: mostrada ao lado, nao ranqueia
    soma_intervalos_estimados_dif: str
    tempo_total_dif_s: float
    tempo_total_dif: str
    fc_dif: float | None
    fc_dif_texto: str | None


class ComparacaoOut(BaseModel):
    forma: str
    a: GrupoOut
    b: GrupoOut
    partes: list[DiferencaParteOut]
    total: DiferencaTotalOut


# ---- texto -----------------------------------------------------------------------------------------------------------

def _hms(s: float) -> str:
    total = int(s + 0.5)
    h, resto = divmod(total, 3600)
    m, seg = divmod(resto, 60)
    return f"{h}:{m:02d}:{seg:02d}"


def _distancia(modalidade: str, m: float | None) -> str | None:
    """Mesma regra da `distancia` da atividade (ADR 0004, adendo 3): natacao em metros, o resto em km."""
    if m is None or m <= 0:
        return None
    if modalidade == "natacao":
        return f"{int(m + 0.5):,}".replace(",", ".") + " m"
    return f"{m / 1000:.2f}".replace(".", ",") + " km"


def _virgula(x: float, casas: int = 1, sinal: bool = False) -> str:
    return f"{x:+.{casas}f}".replace(".", ",") if sinal else f"{x:.{casas}f}".replace(".", ",")


def _ritmo_texto(valor: float, unidade: str) -> str:
    if unidade == "km/h":
        return _virgula(valor) + " km/h"
    return formatar_pace(valor) + (" /km" if unidade == "s/km" else " /100 m")


def _dif_tempo(d: float) -> str:
    return ("+" if d > 0 else "-" if d < 0 else "") + formatar_pace(abs(d))


def _dif_ritmo_texto(d: float, unidade: str) -> str:
    if unidade == "km/h":
        return _virgula(d, sinal=True) + " km/h" if d else "0,0 km/h"
    return _dif_tempo(d) + (" /km" if unidade == "s/km" else " /100 m")


def _dif_fc(d: float) -> str:
    n = int(abs(d) + 0.5)
    return ("+" if d > 0 and n else "-" if d < 0 and n else "") + f"{n} bpm"


def _r1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


# ---- saida -------------------------------------------------------------------------------------------------------------

def _parte_out(ordem: int, p: Parte) -> ParteOut:
    r = ritmo(p)
    return ParteOut(
        ordem=ordem,
        atividade_id=p.atividade_id,
        modalidade=p.modalidade,
        inicio=p.inicio,
        hora_local=inicio_local(p.inicio, p.fuso_min).strftime("%H:%M"),
        duracao_s=_r1(p.duracao_s),
        duracao=_hms(p.duracao_s),
        distancia_m=_r1(p.distancia_m),
        distancia=_distancia(p.modalidade, p.distancia_m),
        fc_media=_r1(p.fc_media),
        ritmo_valor=None if r is None else _r1(r[0]),
        ritmo_unidade=None if r is None else r[1],
        ritmo=None if r is None else _ritmo_texto(*r),
    )


def _grupo_out(g: Grupo) -> GrupoOut:
    primeira = g.partes[0]
    loc = inicio_local(primeira.inicio, primeira.fuso_min)
    intervalos = g.intervalos_estimados_s
    return GrupoOut(
        grupo_id=g.grupo_id,
        forma=g.forma,
        incompleto=g.incompleto,
        inicio=g.inicio,
        fim_estimado=g.fim,
        data_local=loc.date(),
        hora_local=loc.strftime("%H:%M"),
        partes=[_parte_out(i + 1, p) for i, p in enumerate(g.partes)],
        transicoes=[
            IntervaloOut(
                de_atividade_id=a.atividade_id,
                para_atividade_id=b.atividade_id,
                intervalo_estimado_s=_r1(s),
                intervalo_estimado=formatar_pace(s),
            )
            for a, b, s in zip(g.partes, g.partes[1:], intervalos)
        ],
        soma_duracoes_s=_r1(g.soma_duracoes_s),
        soma_duracoes=_hms(g.soma_duracoes_s),
        soma_intervalos_estimados_s=_r1(g.soma_intervalos_estimados_s),
        soma_intervalos_estimados=formatar_pace(g.soma_intervalos_estimados_s),
        tempo_total_s=_r1(g.tempo_total_s),
        tempo_total=_hms(g.tempo_total_s),
        fc_media=_r1(g.fc_media),
    )


def _checar_atleta(session: Session, atleta_id: int) -> None:
    if session.get(Atleta, atleta_id) is None:
        raise HTTPException(status_code=404, detail="atleta não encontrado")


# ---- rotas -------------------------------------------------------------------------------------------------------------

@router.get(
    "/treinos-de-transicao",
    response_model=TreinosDeTransicaoOut,
    operation_id="listarTreinosDeTransicao",
    responses={**_404_ATLETA, 422: {"description": "Período inválido (`inicio` depois de `fim`)"}},
)
def listar_treinos_de_transicao(
    atleta_id: int,
    inicio: date | None = None,
    fim: date | None = None,
    session: Session = Depends(get_session),
) -> TreinosDeTransicaoOut:
    """Os grupos de atividades rotuladas como transição, mais recentes primeiro. `inicio` e `fim` (AAAA-MM-DD) são datas
    locais da primeira parte, inclusivas. O intervalo entre partes é estimado."""
    _periodo_valido(inicio, fim)
    _checar_atleta(session, atleta_id)
    grupos = []
    for g in reversed(grupos_do_atleta(session, atleta_id)):
        d = data_local(g.inicio, g.partes[0].fuso_min)
        if (inicio and d < inicio) or (fim and d > fim):
            continue
        grupos.append(_grupo_out(g))
    return TreinosDeTransicaoOut(periodo=Periodo(inicio=inicio, fim=fim) if (inicio or fim) else None, grupos=grupos)


def _dif_total(a: Grupo, b: Grupo) -> DiferencaTotalOut:
    fc = None if a.fc_media is None or b.fc_media is None else b.fc_media - a.fc_media
    dur = b.soma_duracoes_s - a.soma_duracoes_s
    inter = b.soma_intervalos_estimados_s - a.soma_intervalos_estimados_s
    tot = b.tempo_total_s - a.tempo_total_s
    return DiferencaTotalOut(
        soma_duracoes_dif_s=_r1(dur),
        soma_duracoes_dif=_dif_tempo(dur),
        soma_intervalos_estimados_dif_s=_r1(inter),
        soma_intervalos_estimados_dif=_dif_tempo(inter),
        tempo_total_dif_s=_r1(tot),
        tempo_total_dif=_dif_tempo(tot),
        fc_dif=_r1(fc),
        fc_dif_texto=None if fc is None else _dif_fc(fc),
    )


def _dif_parte(i: int, pa: Parte, pb: Parte) -> DiferencaParteOut:
    ra, rb = ritmo(pa), ritmo(pb)
    rd = None if ra is None or rb is None else rb[0] - ra[0]
    fc = None if pa.fc_media is None or pb.fc_media is None else pb.fc_media - pa.fc_media
    d = pb.duracao_s - pa.duracao_s
    return DiferencaParteOut(
        ordem=i,
        modalidade=pa.modalidade,
        duracao_dif_s=_r1(d),
        duracao_dif=_dif_tempo(d),
        ritmo_dif=_r1(rd),
        ritmo_dif_texto=None if rd is None else _dif_ritmo_texto(rd, ra[1]),
        fc_dif=_r1(fc),
        fc_dif_texto=None if fc is None else _dif_fc(fc),
    )


@router.get(
    "/treinos-de-transicao/comparar",
    response_model=ComparacaoOut,
    operation_id="compararTreinosDeTransicao",
    responses={
        **_404_ATLETA,
        400: {"model": Erro, "description": "Grupos com sequências de modalidades diferentes"},
    },
)
def comparar_treinos_de_transicao(
    atleta_id: int,
    a: int,
    b: int,
    session: Session = Depends(get_session),
) -> ComparacaoOut:
    """Compara dois grupos (`a`, `b` = `grupo_id`) da mesma sequência de modalidades, parte a parte e no total (B menos A).
    O `grupo_id` é derivado: pegue-o da listagem. `404` se não existe ou é de outro atleta; `400` se as formas diferem."""
    _checar_atleta(session, atleta_id)
    por_id = {g.grupo_id: g for g in grupos_do_atleta(session, atleta_id)}
    ga, gb = por_id.get(a), por_id.get(b)
    if ga is None or gb is None:
        raise HTTPException(status_code=404, detail="treino de transição não encontrado")
    if ga.forma != gb.forma:
        raise HTTPException(
            status_code=400,
            detail=f"só se comparam treinos da mesma sequência de modalidades: a é {ga.forma} e b é {gb.forma}",
        )
    return ComparacaoOut(
        forma=ga.forma,
        a=_grupo_out(ga),
        b=_grupo_out(gb),
        partes=[_dif_parte(i + 1, pa, pb) for i, (pa, pb) in enumerate(zip(ga.partes, gb.partes))],
        total=_dif_total(ga, gb),
    )


def transicao_da_atividade(session: Session, atividade_id: int) -> TransicaoOut:
    linha = session.query(RotuloTransicao).filter_by(atividade_id=atividade_id).one_or_none()
    return TransicaoOut(valor=False) if linha is None else TransicaoOut(valor=linha.transicao, origem=linha.origem)


def _atividade_do_atleta(session: Session, atleta_id: int, atividade_id: int) -> Atividade:
    _checar_atleta(session, atleta_id)
    a = session.get(Atividade, atividade_id)
    if a is None or a.atleta_id != atleta_id:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    return a


_404_ATIVIDADE = {404: {"model": Erro, "description": "Atleta ou atividade não encontrados (atividade de outro atleta também)"}}


@router.put(
    "/atividades/{atividade_id}/transicao",
    response_model=TransicaoOut,
    operation_id="corrigirTransicao",
    responses=_404_ATIVIDADE,
)
def corrigir_transicao(
    atleta_id: int,
    atividade_id: int,
    corpo: CorrecaoIn,
    session: Session = Depends(get_session),
) -> TransicaoOut:
    """O atleta marca "sim" ou "não" na atividade, tenha a regra sugerido ou não. Grava `origem = atleta`; a regra nunca mexe nela."""
    _atividade_do_atleta(session, atleta_id, atividade_id)
    agora = datetime.now(timezone.utc)
    linha = session.query(RotuloTransicao).filter_by(atividade_id=atividade_id).one_or_none()
    if linha is None:
        linha = RotuloTransicao(atividade_id=atividade_id)
        session.add(linha)
    linha.transicao, linha.origem, linha.versao_regra, linha.definido_em = corpo.transicao, ORIGEM_ATLETA, None, agora
    session.commit()
    return TransicaoOut(valor=corpo.transicao, origem=ORIGEM_ATLETA)


@router.delete(
    "/atividades/{atividade_id}/transicao",
    status_code=204,
    operation_id="desfazerCorrecaoDeTransicao",
    responses=_404_ATIVIDADE,
)
def desfazer_correcao_de_transicao(
    atleta_id: int,
    atividade_id: int,
    session: Session = Depends(get_session),
) -> Response:
    """Apaga a correção do atleta; a regra volta a valer na próxima rodada de `worker.sugerir_transicao`. Sem correção, não faz
    nada (`204` do mesmo jeito) e nunca apaga uma linha `sugerido`."""
    _atividade_do_atleta(session, atleta_id, atividade_id)
    linha = session.query(RotuloTransicao).filter_by(atividade_id=atividade_id).one_or_none()
    if linha is not None and linha.origem == ORIGEM_ATLETA:
        session.delete(linha)
        session.commit()
    return Response(status_code=204)
