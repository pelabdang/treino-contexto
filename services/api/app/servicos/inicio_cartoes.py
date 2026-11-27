"""Os cartões "Seus números" do início v4 (issue #575; docs/design/telas/inicio-v4.md, docs/metricas/evolucao-series.md).

Cinco cartões, em ordem fixa; **sem dado, o cartão não existe** (a lista só traz os que têm). Tudo é texto pronto: o app não soma, não compara, não
arredonda. Calculado por dia (hoje do atleta), então "Em movimento" só muda quando o dia muda. Descreve, nunca julga: nada de "bom", "meta" ou "sequência".

1. `esta_semana`: treinos, tempo e a semana passada (segunda a domingo local; a semana em curso conta até hoje).
2. `hoje_na_semana`: o que a semana-padrão do atleta prevê para hoje (a rotina dele, sem conselho).
3. `volume_4_semanas`: as 4 semanas completas (4 barras) da modalidade de mais tempo, com a diferença para as 4 anteriores (`frase_evolucao@1`).
4. `em_movimento`: a série de treino ou de tiros cuja mudança entre as janelas da frase é a maior em relação ao piso da série (mínimo 1,0). Volume e
   condicionamento ficam de fora (o 3 já cobre o volume).
5. `melhor_marca`: o recorde do relógio (Garmin) batido nos últimos 30 dias; só os tipos de tempo no formato documentado do leitor de recordes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, RecordePessoal
from app.servicos import evolucao_serie as ev
from app.servicos import evolucao_series as es
from app.servicos import frase_evolucao as fe
from app.servicos import semana_padrao as sp
from app.servicos.fuso import data_local

JANELA_MARCA_DIAS = 30
MINIMO_MOVIMENTO = 1.0  # |d| / piso da série
SEMANAS_COM_VOLUME = 3  # das 4 semanas completas
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
MODALIDADE_ROTULO = {"corrida": "Corrida", "natacao": "Natação", "ciclismo": "Ciclismo"}
VOLUME_DA_MODALIDADE = {"corrida": "corrida.volume_km", "ciclismo": "ciclismo.volume_km", "natacao": "natacao.volume_m"}

Formato = Literal["pequeno", "largo"]


@dataclass(frozen=True)
class Barra:
    data_texto: str  # a segunda-feira da semana: "03/02"
    valor_texto: str  # "10"; a unidade está no `apoio` e no `rotulo`
    destaque: bool  # a semana mais recente


@dataclass(frozen=True)
class Destino:
    tela: Literal["evolucao", "semana_padrao", "treino"]
    serie_id: str | None = None
    atividade_id: int | None = None


@dataclass(frozen=True)
class Cartao:
    id: str
    formato: Formato
    rotulo: str
    valor: str  # o número ou frase curta grande
    apoio: str | None
    texto: str | None  # a frase inteira (Em movimento, Volume)
    barras: list[Barra]
    destino: Destino
    rotulo_acessivel: str


def _duracao(s: float) -> str:
    m = int(s // 60 + (1 if s % 60 >= 30 else 0))  # minutos, meio para cima
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h and m else f"{h} h" if h else f"{m} min"


def _treinos(n: int) -> str:
    return f"{n} treino" if n == 1 else f"{n} treinos"


# ---------- 1. esta semana ----------
def _esta_semana(m: es.Material, destino: Destino) -> Cartao | None:
    seg = es.segunda(m.hoje)
    ant = seg - timedelta(days=7)
    atual = [l for l in m.linhas if seg <= l.dia <= m.hoje]
    if not atual:
        return None
    passada = [l for l in m.linhas if ant <= l.dia < seg]
    tempo = _duracao(sum(l.duracao_s for l in atual))
    apoio = f"{tempo} · semana passada: {len(passada)}" if passada else f"{tempo} · sem semana anterior"
    valor = _treinos(len(atual))
    return Cartao("esta_semana", "pequeno", "Esta semana", valor, apoio, None, [], destino,
                  f"Esta semana, {valor}, {tempo}, " + (f"semana passada {_treinos(len(passada))}" if passada else "sem semana anterior"))


# ---------- 2. hoje na sua semana ----------
def _hoje_na_semana(session: Session, atleta_id: int, hoje: date) -> Cartao | None:
    vigente = sp.vigente_em(session, atleta_id, hoje)
    if vigente is None:
        return None
    itens = sorted((i for i in vigente.itens if i.dia_semana == hoje.isoweekday()), key=lambda i: i.id)
    if not itens:
        return None
    nomes = [f"{MODALIDADE_ROTULO.get(i.modalidade, i.modalidade.capitalize())}{' ' + i.tipo_treino if i.tipo_treino else ''}" for i in itens]
    valor = " e ".join(nomes)
    dia = DIAS[hoje.weekday()]
    return Cartao("hoje_na_semana", "pequeno", f"Hoje, {dia}", valor, "da sua rotina", None, [], Destino("semana_padrao"),
                  f"Hoje, {dia}, {valor}, da sua rotina. Abre a sua semana-padrão.")


# ---------- modalidade principal ----------
def _modalidade_principal(m: es.Material) -> str | None:
    ini = es.segunda(m.hoje) - timedelta(days=7 * 8)
    tempo: dict[str, float] = {}
    for l in m.linhas:
        if l.dia >= ini and l.modalidade in VOLUME_DA_MODALIDADE:
            tempo[l.modalidade] = tempo.get(l.modalidade, 0.0) + l.duracao_s
    return max(sorted(tempo), key=lambda k: tempo[k], default=None)


# ---------- 3. volume das 4 semanas ----------
def _volume(m: es.Material, serie: es.SerieDef) -> Cartao | None:
    brutos = m.pontos_por_serie[serie.id]
    f = ev.frase_da_serie(serie, brutos, m.hoje)
    if f.tipo != "comparada" or f.valor_atual is None or f.valor_anterior is None:
        return None
    seg = es.segunda(m.hoje)
    semanas = es.somar_por_semana(brutos)
    datas = [seg - timedelta(days=7 * k) for k in (4, 3, 2, 1)]
    valores = [semanas.get(d, 0.0) for d in datas]
    if sum(1 for v in valores if v > 0) < SEMANAS_COM_VOLUME:
        return None
    unidade = ev._EIXO[serie.frase][3]
    barras = [Barra(f"{d:%d/%m}", ev.valor_texto(serie.frase, v), i == 3) for i, (d, v) in enumerate(zip(datas, valores))]
    atual, anterior = ev.valor_texto(serie.frase, f.valor_atual), ev.valor_texto(serie.frase, f.valor_anterior)
    if f.mudanca == "parecido":
        apoio = f"parecido com as 4 anteriores ({anterior} {unidade})"
    else:
        dif = ev.valor_texto(serie.frase, abs(f.valor_atual - f.valor_anterior))
        apoio = f"{dif} {unidade} a {'mais' if f.mudanca == 'maior' else 'menos'} que nas 4 anteriores"
    valor = f"{atual} {unidade} por semana"
    return Cartao("volume_4_semanas", "largo", "Volume das 4 semanas", valor, apoio, f.texto, barras, Destino("evolucao", serie.id),
                  f"Volume das 4 semanas, {valor}, {apoio}. Barras: " + "; ".join(f"semana de {b.data_texto}, {b.valor_texto} {unidade}" for b in barras)
                  + ". Abre a evolução do volume.")


# ---------- 4. em movimento ----------
def _em_movimento(m: es.Material) -> Cartao | None:
    melhor: tuple[float, es.SerieDef, fe.FraseEvolucao] | None = None
    for s in es.DEFINICOES:
        if s.tipo not in ("treino", "tiros") or s.id not in m.pontos_por_serie:
            continue
        item = es.avaliar(s, m.pontos_por_serie[s.id], m.hoje)
        if item is None or not item.disponivel:
            continue
        f = ev.frase_da_serie(s, m.pontos_por_serie[s.id], m.hoje)
        if f.tipo != "comparada" or f.mudanca == "parecido" or f.valor_atual is None or f.valor_anterior is None:
            continue
        medida = fe.MEDIDAS[s.frase]
        piso = max(medida.piso_abs, medida.piso_rel * abs(f.valor_anterior))
        razao = abs(f.valor_atual - f.valor_anterior) / piso if piso > 0 else 0.0
        if razao >= MINIMO_MOVIMENTO and (melhor is None or razao > melhor[0] + 1e-9):  # empate: a primeira do catálogo
            melhor = (razao, s, f)
    if melhor is None:
        return None
    _, s, f = melhor
    return Cartao("em_movimento", "largo", "Em movimento", ev.sujeito(s) or s.titulo, None, f.texto, [], Destino("evolucao", s.id),
                  f"Em movimento. {f.texto} Abre a evolução desta série.")


# ---------- 5. melhor marca ----------
_PADRAO_MARCA = re.compile(r"^Best (\d+(?:\.\d+)?)(km|m|mile) (?:Run|Cycle|Pool Swim|Swim)$")
_UNIDADE_MARCA = {"km": "km", "m": "m", "mile": "milha"}


def _nome_da_marca(categoria: str) -> str | None:
    """Nome do tipo de recorde de TEMPO da Garmin ("Best <N><km|m|mile> <Run|Cycle|Pool Swim>", "Best Half Marathon", "Best Marathon"):
    "Best 5km Run" -> "5 km". Qualquer distância desse formato vale; o que não segue o formato (distância, potência, passos) fica fora."""
    c = categoria.strip()
    if c == "Best Half Marathon":
        return "meia maratona"
    if c == "Best Marathon":
        return "maratona"
    m = _PADRAO_MARCA.match(c)
    return None if m is None else f"{m.group(1)} {_UNIDADE_MARCA[m.group(2)]}"


def _tempo(s: float) -> str:
    t = int(s + 0.5)
    h, resto = divmod(t, 3600)
    return f"{h}:{resto // 60:02d}:{resto % 60:02d}" if h else f"{resto // 60}:{resto % 60:02d}"


def _melhor_marca(session: Session, atleta_id: int, hoje: date) -> Cartao | None:
    linhas = session.scalars(select(RecordePessoal).where(RecordePessoal.atleta_id == atleta_id, RecordePessoal.unidade == "s")).all()
    por_categoria: dict[tuple[str, str], list[RecordePessoal]] = {}
    for r in linhas:
        if _nome_da_marca(r.categoria):
            por_categoria.setdefault((r.modalidade, r.categoria), []).append(r)
    recentes: list[tuple[RecordePessoal, bool]] = []
    for grupo in por_categoria.values():
        atual = max(grupo, key=lambda r: r.alcancado_em)  # o recorde vigente: o último a ser batido
        if hoje - timedelta(days=JANELA_MARCA_DIAS) < atual.alcancado_em.date() <= hoje:
            recentes.append((atual, len(grupo) > 1))
    if not recentes:
        return None
    r, melhorou = max(recentes, key=lambda x: (x[0].alcancado_em, x[0].categoria))
    nome, quando = _nome_da_marca(r.categoria), r.alcancado_em.date()
    apoio = f"{'novo recorde' if melhorou else 'recorde do relógio'} · {quando:%d/%m}"
    if len(recentes) > 1:
        apoio += f" · {len(recentes)} marcas no período"
    ativ = session.scalar(select(Atividade.id).where(Atividade.atleta_id == atleta_id, Atividade.fonte_id == r.atividade_fonte_id)) \
        if r.atividade_fonte_id else None
    valor = f"{_tempo(r.valor)} · {nome}"
    return Cartao("melhor_marca", "pequeno", "Melhor marca", valor, apoio, None, [],
                  Destino("treino", None, ativ) if ativ else Destino("evolucao"),
                  f"Melhor marca, {nome}, {_tempo(r.valor)}, {apoio}. Marca do relógio.")


@dataclass(frozen=True)
class Cartoes:
    hoje: date
    cartoes: list[Cartao]


def cartoes(session: Session, atleta_id: int, agora: datetime | None = None) -> Cartoes:
    """Os cartões que têm dado, na ordem fixa (no máximo 5). Lê as atividades uma vez (catálogo), a semana-padrão e os recordes."""
    m = es.carregar(session, atleta_id, agora, tuple(s for s in es.DEFINICOES if s.tipo != "ctl"))
    principal = _modalidade_principal(m)
    serie_volume = es.POR_ID[VOLUME_DA_MODALIDADE[principal]] if principal else None
    destino_semana = Destino("evolucao", serie_volume.id if serie_volume else None)
    candidatos = [
        _esta_semana(m, destino_semana),
        _hoje_na_semana(session, atleta_id, m.hoje),
        None if serie_volume is None else _volume(m, serie_volume),
        _em_movimento(m),
        _melhor_marca(session, atleta_id, m.hoje),
    ]
    return Cartoes(m.hoje, [c for c in candidatos if c is not None])
