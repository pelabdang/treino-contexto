"""Catálogo de séries da Evolução (issue #573; docs/metricas/evolucao-series.md, docs/design/telas/evolucao-v1.md).

Cada série é uma definição (id, título, modalidade, grupo, o filtro de treinos e o valor de cada treino). Os pontos saem de UMA
consulta de colunas das atividades do atleta (mais as sessões de tiros e a série de carga, uma consulta cada): sem N+1, qualquer que
seja o número de séries. Nada é gravado. Data local do treino (ADR 0003); "hoje" é o do atleta (`hoje_do_atleta`).

REGRA DE APARECER (escolha nossa, a do Caio): a série existe para o atleta se ele tem ao menos um treino dela; fica `disponivel` com
8 pontos nas últimas 12 semanas OU o mínimo (3; 2 nos tiros) em cada janela da frase (28 dias até ontem e os 28 anteriores). Volume: 3
semanas com volume nas últimas 12. Condicionamento: 8 dias na janela. Senão `disponivel = false` com o motivo escrito.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade
from app.metricas import carga as cg
from app.servicos.carga_leitura import hoje_do_atleta, serie_do_atleta
from app.servicos.evolucao_tiros import SUBTIPOS_FORA_DA_SERIE, sessoes_tiros_1km
from app.servicos.fuso import data_local

JANELA_GRAFICO_DIAS = 84  # 12 semanas, o período inicial do gráfico
JANELA_FRASE_DIAS = 28
MINIMO_PONTOS_12S = 8  # o mesmo mínimo da linha de base
MINIMO_JANELA = 3
MINIMO_JANELA_TIROS = 2  # igual ao mínimo de `tiros_1km@6`
MINIMO_SEMANAS_VOLUME = 3
MINIMO_DIAS_CTL = 8

Modalidade = Literal["corrida", "natacao", "ciclismo", "geral"]
Grupo = Literal["Ritmo", "Coração", "Esforço e volume", "Marcas"]
Tipo = Literal["treino", "volume", "ctl", "tiros"]
ORDEM_MODALIDADE = ("corrida", "natacao", "ciclismo", "geral")
ORDEM_GRUPO = ("Ritmo", "Coração", "Esforço e volume", "Marcas")


@dataclass(frozen=True)
class Linha:
    """O que a série lê de cada atividade (só colunas)."""

    id: int
    modalidade: str
    subtipo: str | None
    dia: date  # data local
    inicio: datetime
    duracao_s: float
    distancia_m: float | None
    fc_media: float | None
    tipo_treino: str | None
    fuso_min: int | None = None


@dataclass(frozen=True)
class PontoSerie:
    dia: date
    valor: float | None  # None: o treino é da série mas sem a medida (ex.: sem FC)
    atividade_id: int | None
    aprendendo: bool = False


@dataclass(frozen=True)
class SerieDef:
    id: str
    titulo: str
    descricao: str  # o que o gráfico mostra, uma linha
    modalidade: Modalidade
    grupo: Grupo
    tipo: Tipo
    frase: str  # tipo da `frase_evolucao` (pace_km, fc, volume_km...)
    plural: str  # para o motivo: "Poucos/Poucas {plural} nas últimas 12 semanas"
    pertence: Callable[[Linha], bool] = lambda l: False
    valor: Callable[[Linha], float | None] = lambda l: None


@dataclass(frozen=True)
class ItemCatalogo:
    serie: SerieDef
    n_pontos: int
    disponivel: bool
    motivo: str | None


@dataclass(frozen=True)
class Catalogo:
    hoje: date
    itens: list[ItemCatalogo]
    serie_padrao: str | None


# ---------- valores por treino ----------
def _pace_km(l: Linha) -> float | None:
    return l.duracao_s / l.distancia_m * 1000 if l.distancia_m and l.distancia_m > 0 and l.duracao_s > 0 else None


def _ritmo_100m(l: Linha) -> float | None:
    return l.duracao_s / l.distancia_m * 100 if l.distancia_m and l.distancia_m > 0 and l.duracao_s > 0 else None


def _velocidade_kmh(l: Linha) -> float | None:
    return l.distancia_m / 1000 / (l.duracao_s / 3600) if l.distancia_m and l.distancia_m > 0 and l.duracao_s > 0 else None


def _fc(l: Linha) -> float | None:
    return l.fc_media if l.fc_media and l.fc_media > 0 else None


def _km(l: Linha) -> float | None:
    return l.distancia_m / 1000 if l.distancia_m else None


def _horas(l: Linha) -> float | None:
    return l.duracao_s / 3600 if l.duracao_s else None


def _metros(l: Linha) -> float | None:
    return l.distancia_m or None


def _ambiente_ciclismo(l: Linha) -> str:
    """Na rua (ar livre) ou em casa (virtual e rolo; subtipo `esteira` no ciclismo = bicicleta em rolo/indoor): duas séries (decisão do Angelo, 27/11)."""
    return "casa" if l.subtipo in ("virtual", "esteira") else "rua"


_TIPOS = ("leve", "moderado", "longo")
_ROTULO_TIPO = {"leve": "leves", "moderado": "moderados", "longo": "longos"}
_AMBIENTES = {"rua": "na rua", "casa": "em casa"}


def _definicoes() -> list[SerieDef]:
    d: list[SerieDef] = []
    d.append(SerieDef("corrida.tiros", "Melhor tiro de 1 km", "O pace do melhor tiro de 1 km de cada sessão de tiros", "corrida", "Ritmo",
                      "tiros", "pace_km", "treinos de tiros de 1 km"))
    for t in _TIPOS:
        d.append(SerieDef(f"corrida.pace.{t}", f"Pace dos treinos {_ROTULO_TIPO[t]}", f"O pace médio de cada treino {t} de corrida", "corrida",
                          "Ritmo", "treino", "pace_km", f"treinos {_ROTULO_TIPO[t]} de corrida",
                          lambda l, t=t: l.modalidade == "corrida" and l.tipo_treino == t and l.subtipo not in SUBTIPOS_FORA_DA_SERIE,
                          _pace_km))
    for t in _TIPOS:
        d.append(SerieDef(f"corrida.fc.{t}", f"FC dos treinos {_ROTULO_TIPO[t]}", f"A frequência cardíaca média de cada treino {t} de corrida", "corrida",
                          "Coração", "treino", "fc", f"treinos {_ROTULO_TIPO[t]} de corrida com FC",
                          lambda l, t=t: l.modalidade == "corrida" and l.tipo_treino == t, _fc))
    d.append(SerieDef("corrida.volume_km", "Volume por semana (km)", "Os quilômetros corridos em cada semana", "corrida", "Esforço e volume",
                      "volume", "volume_km", "semanas com corrida", lambda l: l.modalidade == "corrida", _km))
    d.append(SerieDef("corrida.volume_h", "Volume por semana (horas)", "As horas corridas em cada semana", "corrida", "Esforço e volume",
                      "volume", "volume_h", "semanas com corrida", lambda l: l.modalidade == "corrida", _horas))
    d.append(SerieDef("natacao.ritmo", "Ritmo na piscina", "O ritmo médio por 100 m de cada treino de piscina, com as pausas", "natacao", "Ritmo",
                      "treino", "pace_100m", "treinos de piscina", lambda l: l.modalidade == "natacao" and l.subtipo == "piscina", _ritmo_100m))
    d.append(SerieDef("natacao.fc", "FC na natação", "A frequência cardíaca média de cada treino de natação", "natacao", "Coração",
                      "treino", "fc", "treinos de natação com FC", lambda l: l.modalidade == "natacao", _fc))
    d.append(SerieDef("natacao.volume_m", "Volume por semana (m)", "Os metros nadados em cada semana", "natacao", "Esforço e volume",
                      "volume", "volume_m", "semanas com natação", lambda l: l.modalidade == "natacao", _metros))
    for amb, rot in _AMBIENTES.items():
        d.append(SerieDef(f"ciclismo.velocidade.{amb}", f"Velocidade {rot}", f"A velocidade média de cada pedal {rot}", "ciclismo", "Ritmo",
                          "treino", "velocidade", f"pedais {rot}",
                          lambda l, amb=amb: l.modalidade == "ciclismo" and _ambiente_ciclismo(l) == amb, _velocidade_kmh))
    for amb, rot in _AMBIENTES.items():
        d.append(SerieDef(f"ciclismo.fc.{amb}", f"FC no pedal {rot}", f"A frequência cardíaca média de cada pedal {rot}", "ciclismo", "Coração",
                          "treino", "fc", f"pedais {rot} com FC",
                          lambda l, amb=amb: l.modalidade == "ciclismo" and _ambiente_ciclismo(l) == amb, _fc))
    d.append(SerieDef("ciclismo.volume_km", "Volume por semana (km)", "Os quilômetros pedalados em cada semana", "ciclismo", "Esforço e volume",
                      "volume", "volume_km", "semanas com pedal", lambda l: l.modalidade == "ciclismo", _km))
    d.append(SerieDef("geral.ctl", "Condicionamento", "O condicionamento (CTL) de cada dia", "geral", "Esforço e volume", "ctl", "ctl",
                      "dias com condicionamento calculado"))
    return d


DEFINICOES: tuple[SerieDef, ...] = tuple(_definicoes())
POR_ID: dict[str, SerieDef] = {s.id: s for s in DEFINICOES}


# ---------- leitura (uma consulta de colunas) ----------
def ler_linhas(session: Session, atleta_id: int) -> list[Linha]:
    """As atividades do atleta (fora o pai multiesporte e a troca, como a carga), por data local e id. Uma consulta, só colunas."""
    q = select(Atividade.id, Atividade.modalidade, Atividade.subtipo, Atividade.inicio, Atividade.fuso_min, Atividade.duracao_s,
               Atividade.distancia_m, Atividade.fc_media, Atividade.tipo_treino).where(Atividade.atleta_id == atleta_id)
    linhas = [Linha(i, m, s, data_local(ini, fuso), ini, dur, dist, fc, tipo, fuso)
              for i, m, s, ini, fuso, dur, dist, fc, tipo in session.execute(q) if not cg.ignorada(s)]
    linhas.sort(key=lambda l: (l.dia, l.id))
    return linhas


def pontos_por_treino(s: SerieDef, linhas: list[Linha]) -> list[PontoSerie]:
    return [PontoSerie(l.dia, s.valor(l), l.id) for l in linhas if s.pertence(l)]


def segunda(d: date) -> date:
    return d - timedelta(days=d.weekday())


def somar_por_semana(pontos: list[PontoSerie]) -> dict[date, float]:
    """Soma por semana ISO local (segunda a domingo), só das semanas com treino; as sem treino valem 0 em quem as lê."""
    por: dict[date, float] = {}
    for p in pontos:
        por[segunda(p.dia)] = por.get(segunda(p.dia), 0.0) + (p.valor or 0.0)
    return por


@dataclass(frozen=True)
class Material:
    """Tudo o que as séries leem, carregado uma vez por pedido."""

    hoje: date
    linhas: list[Linha]
    tiros: list[PontoSerie]
    ctl: list[PontoSerie]  # um por dia
    pontos_por_serie: dict[str, list[PontoSerie]]


def carregar(session: Session, atleta_id: int, agora: datetime | None = None, series: tuple[SerieDef, ...] = DEFINICOES) -> Material:
    """Lê só o que as `series` pedidas precisam: as sessões de tiros e a carga só se alguma delas for de tiros ou de condicionamento."""
    linhas = ler_linhas(session, atleta_id)
    mais_recente = max(linhas, key=lambda l: l.inicio, default=None)
    hoje = hoje_do_atleta(None if mais_recente is None else mais_recente.fuso_min, agora)
    tiros = ([PontoSerie(x.ponto.data, x.ponto.melhor_pace_s_km, x.ponto.atividade_id) for x in sessoes_tiros_1km(session, atleta_id)]
             if any(s.tipo == "tiros" for s in series) else [])
    ctl = ([PontoSerie(d.dia, d.ctl, None, d.aprendendo) for d in serie_do_atleta(session, atleta_id, agora).serie.dias]
           if any(s.tipo == "ctl" for s in series) else [])
    por: dict[str, list[PontoSerie]] = {}
    for s in series:
        por[s.id] = tiros if s.tipo == "tiros" else ctl if s.tipo == "ctl" else pontos_por_treino(s, linhas)
    return Material(hoje, linhas, tiros, ctl, por)


# ---------- catálogo ----------
def _com_valor(pontos: list[PontoSerie]) -> list[PontoSerie]:
    return [p for p in pontos if p.valor is not None]


def _janelas(hoje: date) -> tuple[tuple[date, date], tuple[date, date]]:
    ontem = hoje - timedelta(days=1)
    r = (ontem - timedelta(days=JANELA_FRASE_DIAS - 1), ontem)
    a = (r[0] - timedelta(days=JANELA_FRASE_DIAS), r[0] - timedelta(days=1))
    return r, a


def _conta(pontos: list[PontoSerie], ini: date, fim: date) -> int:
    return sum(1 for p in pontos if ini <= p.dia <= fim)


def avaliar(s: SerieDef, pontos: list[PontoSerie], hoje: date) -> ItemCatalogo | None:
    """None: a série não existe para o atleta (nenhum treino dela)."""
    if not pontos:
        return None
    ini12 = hoje - timedelta(days=JANELA_GRAFICO_DIAS - 1)
    if s.tipo == "volume":
        semanas = somar_por_semana(pontos)
        n = sum(1 for sem, v in semanas.items() if v > 0 and segunda(hoje) - timedelta(days=77) <= sem <= segunda(hoje))
        ok = n >= MINIMO_SEMANAS_VOLUME
    elif s.tipo == "ctl":
        n = _conta(pontos, ini12, hoje)
        ok = n >= MINIMO_DIAS_CTL
    else:
        validos = _com_valor(pontos)
        n = _conta(validos, ini12, hoje)
        (r0, r1), (a0, a1) = _janelas(hoje)
        minimo = MINIMO_JANELA_TIROS if s.tipo == "tiros" else MINIMO_JANELA
        ok = n >= MINIMO_PONTOS_12S or (_conta(validos, r0, r1) >= minimo and _conta(validos, a0, a1) >= minimo)
    pouco = "Poucas" if s.plural.startswith("semanas") else "Poucos"
    return ItemCatalogo(s, n, ok, None if ok else f"{pouco} {s.plural} nas últimas 12 semanas")


def _serie_padrao(itens: list[ItemCatalogo], linhas: list[Linha], m: Material) -> str | None:
    """A do último treino (a primeira disponível que o contém, de preferência de ritmo ou de coração); senão a primeira disponível."""
    disp = [i for i in itens if i.disponivel]
    if not disp:
        return None
    if linhas:
        ultimo = max(linhas, key=lambda l: (l.inicio, l.id))
        for i in disp:
            if i.serie.tipo == "treino" and any(p.atividade_id == ultimo.id for p in m.pontos_por_serie[i.serie.id]):
                return i.serie.id
        for i in disp:
            if i.serie.tipo == "tiros" and any(p.atividade_id == ultimo.id for p in m.tiros):
                return i.serie.id
    return disp[0].serie.id


def catalogo(session: Session, atleta_id: int, agora: datetime | None = None) -> Catalogo:
    m = carregar(session, atleta_id, agora)
    itens = [i for s in DEFINICOES if (i := avaliar(s, m.pontos_por_serie[s.id], m.hoje)) is not None]
    itens.sort(key=lambda i: (ORDEM_MODALIDADE.index(i.serie.modalidade), ORDEM_GRUPO.index(i.serie.grupo), DEFINICOES.index(i.serie)))
    return Catalogo(m.hoje, itens, _serie_padrao(itens, m.linhas, m))
