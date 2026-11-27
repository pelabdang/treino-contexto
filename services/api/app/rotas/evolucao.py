"""Rotas da evolução dos tiros de 1 km (issue #16)."""

from __future__ import annotations

from datetime import date, datetime

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Atleta
from app.graficos.escala import Escala, escala_fc, escala_pace
from app.graficos.tiros_1km import render_png
from app.db.session import get_session
from app.metricas.tiros_1km import VERSAO, formatar_pace
from app.servicos import evolucao_serie as ev
from app.servicos import evolucao_series as es
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
    # Melhor tiro (ADR 0004, adendo 1): valor principal do gráfico; a média acima é a secundária.
    pace_melhor_s_km: float
    pace_melhor: str  # m:ss, de formatar_pace sobre o valor sem arredondar
    fc_melhor_tiro: float | None  # FC do melhor tiro; null se ele não tem FC (não troca de tiro)
    ordem_melhor_tiro: int  # `ordem` do melhor tiro em `tiros`
    tiros: list[TiroOut]


class MarcaPace(BaseModel):
    valor_s_km: float
    rotulo: str  # m:ss, de formatar_pace


class EixoPace(BaseModel):
    min_s_km: float
    max_s_km: float
    invertido: bool  # pace menor (mais rápido) fica no alto
    marcas: list[MarcaPace]


class MarcaFc(BaseModel):
    valor_bpm: float
    rotulo: str


class EixoFc(BaseModel):
    min_bpm: float
    max_bpm: float
    marcas: list[MarcaFc]


class Eixos(BaseModel):
    pace: EixoPace | None  # null se não há pace (nunca ocorre com sessões)
    fc: EixoFc | None  # null se nenhuma sessão tem FC


class EvolucaoTiros1km(BaseModel):
    atleta_id: int
    metrica: Literal["tiros_1km"]
    versao_calculo: str  # sempre a VERSAO da regra atual
    reclassificacao_pendente: bool  # há segmento gravado com outra versao_deteccao
    unidades: Unidades
    periodo: Periodo | None
    eixos: Eixos | None  # null sem sessões; mesma escala do PNG (escala_eixo, #63)
    sessoes: list[SessaoOut]


def _um_decimal(v: float | None) -> float | None:
    return None if v is None else round(v, 1)


def _eixos(sessoes: list[SessaoSerie]) -> Eixos | None:
    """Eixos pela regra de `escala_eixo`, sobre o valor principal (melhor tiro) sem arredondar (1 casa só na saída)."""
    if not sessoes:
        return None
    pace: Escala | None = escala_pace([s.ponto.melhor_pace_s_km for s in sessoes])
    fc: Escala | None = escala_fc([s.ponto.melhor_fc_media for s in sessoes])
    return Eixos(
        pace=None if pace is None else EixoPace(
            min_s_km=round(pace.min, 1), max_s_km=round(pace.max, 1), invertido=True,
            marcas=[MarcaPace(valor_s_km=round(m.valor, 1), rotulo=m.rotulo) for m in pace.marcas]),
        fc=None if fc is None else EixoFc(
            min_bpm=round(fc.min, 1), max_bpm=round(fc.max, 1),
            marcas=[MarcaFc(valor_bpm=round(m.valor, 1), rotulo=m.rotulo) for m in fc.marcas]),
    )


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
        pace_melhor_s_km=_um_decimal(p.melhor_pace_s_km),
        pace_melhor=formatar_pace(p.melhor_pace_s_km),
        fc_melhor_tiro=_um_decimal(p.melhor_fc_media),
        ordem_melhor_tiro=p.melhor_ordem,
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
    """Melhor tiro (principal) e média dos tiros de 1 km por sessão. `inicio` e `fim` (AAAA-MM-DD) são datas locais, inclusivas."""
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
        eixos=_eixos(sessoes),
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


class SerieCatalogoOut(BaseModel):
    id: str  # ex.: corrida.pace.leve; estável, o app guarda a última escolhida
    titulo: str
    descricao: str  # uma linha: o que o gráfico mostra
    modalidade: Literal["corrida", "natacao", "ciclismo", "geral"]
    grupo: Literal["Ritmo", "Coração", "Esforço e volume", "Marcas"]
    n_pontos: int  # pontos com valor nas últimas 12 semanas (volume: semanas com volume; condicionamento: dias)
    disponivel: bool
    motivo: str | None  # texto pronto quando não disponível ("Poucos treinos ... nas últimas 12 semanas"); null se disponível


class CatalogoSeriesOut(BaseModel):
    atleta_id: int
    series: list[SerieCatalogoOut]  # só as séries com ao menos um treino do atleta, por modalidade, grupo e ordem do catálogo
    serie_padrao: str | None  # a do último treino, entre as disponíveis; null sem nenhuma disponível


@router.get("/series", response_model=CatalogoSeriesOut, operation_id="catalogoSeriesEvolucao", responses=_ERRO_404)
def catalogo_series(atleta_id: int, session: Session = Depends(get_session)) -> CatalogoSeriesOut:
    """O catálogo de séries da Evolução do atleta (#573). Uma série aparece se o atleta tem treino dela; `disponivel` segue a regra do Caio
    (8 pontos nas últimas 12 semanas ou o mínimo em cada janela da frase); indisponível vem com o motivo escrito, nunca some."""
    _atleta_ou_404(session, atleta_id)
    c = es.catalogo(session, atleta_id)
    return CatalogoSeriesOut(
        atleta_id=atleta_id,
        series=[SerieCatalogoOut(id=i.serie.id, titulo=i.serie.titulo, descricao=i.serie.descricao, modalidade=i.serie.modalidade,
                                 grupo=i.serie.grupo, n_pontos=i.n_pontos, disponivel=i.disponivel, motivo=i.motivo) for i in c.itens],
        serie_padrao=c.serie_padrao,
    )


class PontoSerieOut(BaseModel):
    atividade_id: int | None  # null onde o ponto não é um treino (volume por semana, condicionamento): sem "Abrir treino"
    data: date  # data local do treino; segunda-feira da semana no volume
    data_texto: str  # "ter 18/03"; "semana de 10/03" no volume
    valor: float | None  # 1 casa; só para desenhar. Pace e ritmo em s/km e s/100 m
    valor_texto: str | None  # pronto: "5:42", "150", "25,3"; a unidade vem em `unidade`. null sem valor e no condicionamento que ainda aprende
    melhor: bool  # losango: o melhor do período (só em pace, ritmo e velocidade)
    fora_do_normal: bool | None  # triângulo: o selo do PRÓPRIO treino (linha_base@3 dele, 84 dias antes); null sem selo ou aprendendo
    normal_estado: Literal["fora", "dentro", "aprendendo"] | None  # o mesmo selo da lista e da tela do treino
    aprendendo: bool  # condicionamento: o dia ainda aprende (linha pontilhada)
    parcial: bool  # volume: a semana em curso
    rotulo: str  # o que o leitor de tela lê no ponto


class ReferenciaOut(BaseModel):
    minimo: float
    maximo: float
    mediana: float
    n: int  # pontos que a calcularam
    texto: str  # "Seu normal 5:16 a 6:08"


class MarcaEixoOut(BaseModel):
    valor: float
    rotulo: str


class EixoSerieOut(BaseModel):
    minimo: float
    maximo: float
    invertido: bool  # menor no alto (pace e ritmo: "mais rápido ↑")
    marcas: list[MarcaEixoOut]


class FraseEvolucaoOut(BaseModel):
    """`frase_evolucao@1`: as 4 semanas até ontem contra as 4 anteriores, qualquer que seja o período. Descreve, não aconselha."""

    versao: str
    tipo: Literal["comparada", "poucos", "sem_treino", "so_valor", "sem_dado"]
    mudanca: Literal["maior", "menor", "parecido"] | None
    a_favor: bool | None  # só para ícone; nunca entra no texto
    texto: str
    valor_atual: float | None
    valor_anterior: float | None
    n_atual: int
    n_anterior: int


class SerieEvolucaoOut(BaseModel):
    atleta_id: int
    id: str
    titulo: str
    descricao: str
    modalidade: Literal["corrida", "natacao", "ciclismo", "geral"]
    grupo: Literal["Ritmo", "Coração", "Esforço e volume", "Marcas"]
    periodo: Literal["12s", "6m", "1a"]
    inicio: date  # primeiro dia do período (data local)
    fim: date  # hoje do atleta
    unidade: str  # "/km", "bpm", "km/h", "km", "h", "m", "/100 m"; vazio no condicionamento
    versao_calculo: str
    pontos: list[PontoSerieOut]  # do mais antigo ao mais recente
    ultimo_valor_texto: str | None  # o número grande
    ultimo_rotulo: str | None  # "último treino, ter 18/03"
    referencia: ReferenciaOut | None  # a faixa do normal; null sem 8 treinos (ver `aprendendo_texto`) e nas séries sem faixa
    aprendendo_texto: str | None
    eixo: EixoSerieOut | None  # null sem pontos
    frase: FraseEvolucaoOut


@router.get("/series/{serie_id}", response_model=SerieEvolucaoOut, operation_id="serieEvolucao",
            responses={404: {"model": Erro, "description": "Atleta ou série não encontrados"}})
def serie_evolucao(atleta_id: int, serie_id: str, periodo: Literal["12s", "6m", "1a"] = "12s",
                   session: Session = Depends(get_session)) -> SerieEvolucaoOut:
    """Uma série da Evolução (#574): pontos com texto pronto e `atividade_id`, eixo, faixa do normal, destaques e a frase. `periodo`: 12 semanas
    (padrão), 6 meses ou 1 ano; a frase não muda com ele. Série do catálogo sem treino do atleta devolve pontos vazios e a frase "sem treino"."""
    _atleta_ou_404(session, atleta_id)
    if serie_id not in es.POR_ID:
        raise HTTPException(status_code=404, detail="série não encontrada")
    r = ev.serie(session, atleta_id, serie_id, periodo)
    s = r.serie
    return SerieEvolucaoOut(
        atleta_id=atleta_id, id=s.id, titulo=s.titulo, descricao=s.descricao, modalidade=s.modalidade, grupo=s.grupo, periodo=r.periodo,
        inicio=r.inicio, fim=r.fim, unidade=r.unidade, versao_calculo=r.versao_calculo,
        pontos=[PontoSerieOut(**vars(p)) for p in r.pontos],
        ultimo_valor_texto=r.ultimo_valor_texto, ultimo_rotulo=r.ultimo_rotulo,
        referencia=None if r.referencia is None else ReferenciaOut(**vars(r.referencia)),
        aprendendo_texto=r.aprendendo_texto,
        eixo=None if r.eixo is None else EixoSerieOut(minimo=r.eixo.minimo, maximo=r.eixo.maximo, invertido=r.eixo.invertido,
                                                       marcas=[MarcaEixoOut(valor=m.valor, rotulo=m.rotulo) for m in r.eixo.marcas]),
        frase=FraseEvolucaoOut(**vars(r.frase)),
    )
