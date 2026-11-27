"""Uma série da Evolução com janela, frase e referência (issue #574; docs/design/telas/evolucao-v1.md).

Tudo calculado aqui; o app só desenha: pontos com texto pronto, eixos, a faixa do normal, destaques (melhor, fora do normal) e a frase
(`frase_evolucao@1`, `app/servicos/frase_evolucao.py`). A frase não depende do período do gráfico (4 semanas até ontem contra as 4 anteriores).

FAIXA DO NORMAL (escolha nossa, a mesma conta da `linha_base@3` para o selo e o gráfico não discordarem): mediana e desvio robusto
(`medida_robusta`, com o piso da métrica) dos pontos das 12 semanas até ontem; a faixa é mediana ± 2,5 desvios (o `limite_fora` da linha de base);
Só com 8 pontos (o mínimo da linha de base); com menos, `aprendendo` e a faixa não existe. Só em séries de treino e de tiros (volume e condicionamento não têm
faixa). A faixa é o normal DE AGORA, contexto visual.

O TRIÂNGULO (`fora_do_normal`) NÃO sai da faixa: é o selo do próprio treino (`normal_treino@1` sobre a `linha_base@3` dele, 84 dias ANTES do treino, a mesma
da lista e da tela do treino), em lote (`linha_base_resultados`, sem N+1). Assim o gráfico, a lista e o treino nunca discordam. Observação: o selo é do
treino inteiro (qualquer métrica fora), não só da métrica da série.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.servicos.linha_base_leitura import linha_base_resultados

from app.graficos.escala import Escala, escala_eixo
from app.db.models import Atividade
from app.metricas import linha_base as lb
from app.metricas.normal_treino import normal_treino
from app.metricas.tiros_1km import formatar_pace
from app.servicos import frase_evolucao as fe
from app.servicos.evolucao_series import (
    JANELA_GRAFICO_DIAS, POR_ID, SerieDef, PontoSerie, carregar, segunda, somar_por_semana,
)

VERSAO = "evolucao_serie@1"
PERIODOS = {"12s": JANELA_GRAFICO_DIAS, "6m": 182, "1a": 365}
Periodo = Literal["12s", "6m", "1a"]
SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
FORA_DESVIOS = lb.PADRAO.limite_fora

# frase -> (amplitude mínima do eixo, passo, eixo invertido (menor no alto), unidade, chave do piso da linha de base)
_EIXO = {
    "pace_km": (30.0, 10.0, True, "/km", "pace_medio"),
    "pace_100m": (10.0, 5.0, True, "/100 m", "pace_medio"),
    "fc": (5.0, 1.0, False, "bpm", "fc_media"),
    "velocidade": (5.0, 1.0, False, "km/h", "pace_medio"),
    "volume_km": (10.0, 5.0, False, "km", None),
    "volume_h": (2.0, 1.0, False, "h", None),
    "volume_m": (1000.0, 500.0, False, "m", None),
    "ctl": (10.0, 5.0, False, "", None),
}
_MELHOR = {"pace_km": min, "pace_100m": min, "velocidade": max}  # as séries com "melhor treino"


@dataclass(frozen=True)
class PontoOut:
    atividade_id: int | None
    data: date
    data_texto: str
    valor: float | None
    valor_texto: str | None
    melhor: bool
    fora_do_normal: bool | None
    normal_estado: str | None  # o selo do treino: fora, dentro, aprendendo ou None
    aprendendo: bool
    parcial: bool
    rotulo: str


@dataclass(frozen=True)
class Referencia:
    minimo: float
    maximo: float
    mediana: float
    n: int
    texto: str


@dataclass(frozen=True)
class Marca:
    valor: float
    rotulo: str


@dataclass(frozen=True)
class Eixo:
    minimo: float
    maximo: float
    invertido: bool
    marcas: list[Marca]


@dataclass(frozen=True)
class SerieLida:
    serie: SerieDef
    periodo: str
    inicio: date
    fim: date
    unidade: str
    pontos: list[PontoOut]
    ultimo_valor_texto: str | None
    ultimo_rotulo: str | None
    referencia: Referencia | None
    aprendendo_texto: str | None
    eixo: Eixo | None
    frase: fe.FraseEvolucao
    versao_calculo: str


# ---------- textos ----------
def _num(x: float, casas: int) -> str:
    s = f"{x:.{casas}f}".replace(".", ",")
    return s[:-2] if casas and s.endswith(",0") else s


def valor_texto(frase_tipo: str, x: float) -> str:
    """O valor sem a unidade (a unidade vai à parte)."""
    if frase_tipo in ("pace_km", "pace_100m"):
        return formatar_pace(x)
    if frase_tipo in ("fc", "ctl"):
        return str(int(fe.arredonda(x)))
    if frase_tipo == "volume_m":
        return f"{int(fe.arredonda(x)):,}".replace(",", ".")
    return _num(fe.arredonda(x, 1), 1)


def data_texto(d: date) -> str:
    return f"{SEMANA[d.weekday()]} {d:%d/%m}"


def sujeito(s: SerieDef) -> str | None:
    """O sujeito da frase ("Pace dos seus treinos leves"); None no condicionamento."""
    if s.id == "corrida.tiros":
        return "Melhor tiro de 1 km"
    if s.tipo == "volume":
        return {"corrida": "Volume de corrida", "natacao": "Volume de natação", "ciclismo": "Volume de pedal"}[s.modalidade]
    if s.tipo == "ctl":
        return None
    if s.id == "natacao.ritmo":
        return "Ritmo dos seus treinos de piscina"
    if s.modalidade == "natacao":
        return "Frequência cardíaca dos seus treinos de natação"
    nome = "Frequência cardíaca" if s.frase == "fc" else "Pace" if s.frase == "pace_km" else "Velocidade"
    sufixo = s.id.split(".")[-1]
    if s.modalidade == "corrida":
        return f"{nome} dos seus treinos {dict(leve='leves', moderado='moderados', longo='longos')[sufixo]}"
    return f"{nome} dos seus pedais {dict(ar_livre='ao ar livre', virtual='virtuais', rolo='no rolo')[sufixo]}"


def _rotulo_ponto(s: SerieDef, dia: date, data_t: str, valor: float | None, texto: str | None, fora: bool | None, unidade: str) -> str:
    """A frase que o leitor de tela lê no ponto: "Treino de 18/03, 5:42 por quilômetro, dentro do seu normal"."""
    if valor is None:
        return f"{data_t}, sem valor"
    if s.tipo == "volume":
        base = f"Semana de {dia:%d/%m}, {texto} {unidade}"
    elif s.tipo == "ctl":
        base = f"Dia {dia:%d/%m}, condicionamento {texto}" if texto else f"Dia {dia:%d/%m}, ainda aprendendo"
    else:
        base = f"Treino de {dia:%d/%m}, {texto} {unidade}".replace("/km", "por quilômetro").replace("/100 m", "por 100 metros")
    if fora is not None:
        base += ", fora do seu normal" if fora else ", dentro do seu normal"
    return base


# ---------- referência ----------
def _referencia(s: SerieDef, pontos: list[PontoSerie], hoje: date, unidade: str) -> tuple[Referencia | None, str | None]:
    if s.tipo not in ("treino", "tiros"):
        return None, None
    ontem = hoje - timedelta(days=1)
    valores = [p.valor for p in pontos if p.valor is not None and ontem - timedelta(days=JANELA_GRAFICO_DIAS - 1) <= p.dia <= ontem]
    minimo = lb.PADRAO.minimo_treinos
    if len(valores) < minimo:
        k = minimo - len(valores)
        return None, f"Ainda estamos aprendendo o seu normal: {'falta 1 treino' if k == 1 else f'faltam {k} treinos'} para mostrar a faixa."
    chave = _EIXO[s.frase][4]
    mediana, desvio = lb.medida_robusta(valores, lb.PADRAO, chave)
    lo, hi = mediana - FORA_DESVIOS * desvio, mediana + FORA_DESVIOS * desvio
    a, b = valor_texto(s.frase, lo), valor_texto(s.frase, hi)
    sufixo = "" if s.frase in ("pace_km", "pace_100m") else f" {unidade}"
    return Referencia(lo, hi, mediana, len(valores), f"Seu normal {a} a {b}{sufixo}"), None


# ---------- série ----------
def _pontos_do_periodo(s: SerieDef, brutos: list[PontoSerie], ini: date, hoje: date) -> list[PontoSerie]:
    if s.tipo == "volume":
        semanas = somar_por_semana(brutos)
        out, d = [], segunda(hoje) - timedelta(days=7 * ((hoje - ini).days + 1) // 7 - 7)  # as últimas N semanas, a em curso incluída
        while d <= hoje:
            out.append(PontoSerie(d, semanas.get(d, 0.0), None))
            d += timedelta(days=7)
        return out
    return [p for p in brutos if ini <= p.dia <= hoje]


def _eixo(frase_tipo: str, valores: list[float]) -> Eixo | None:
    amp, passo, invertido, _, _ = _EIXO[frase_tipo]
    esc: Escala | None = escala_eixo(valores, amp, passo, lambda v: valor_texto(frase_tipo, v))
    if esc is None:
        return None
    return Eixo(round(esc.min, 1), round(esc.max, 1), invertido, [Marca(round(m.valor, 1), m.rotulo) for m in esc.marcas])


def frase_da_serie(s: SerieDef, brutos: list[PontoSerie], hoje: date) -> fe.FraseEvolucao:
    """A frase da série sobre os pontos por treino (por dia no condicionamento); os tiros pedem 2 por janela."""
    return fe.frase_evolucao(s.frase, [fe.Ponto(p.dia, p.valor, p.aprendendo) for p in brutos], hoje, sujeito(s), 2 if s.tipo == "tiros" else None)


def _selos(session: Session, ids: list[int]) -> dict[int, str | None]:
    """O selo "normal" de cada treino (`normal_treino@1` sobre a `linha_base@3`), com uma consulta de historico para todos."""
    if not ids:
        return {}
    ativs = list(session.scalars(select(Atividade).where(Atividade.id.in_(ids))))
    bases = linha_base_resultados(session, ativs)
    return {i: normal_treino(b.estado, [m.estado for m in b.metricas]) for i, b in bases.items()}


def serie(session: Session, atleta_id: int, serie_id: str, periodo: Periodo = "12s", agora: datetime | None = None) -> SerieLida:
    """`KeyError` se `serie_id` não existe no catálogo. Série sem treino do atleta devolve pontos vazios e a frase "sem treino"."""
    s = POR_ID[serie_id]
    m = carregar(session, atleta_id, agora, (s,))
    hoje, brutos = m.hoje, m.pontos_por_serie[s.id]
    unidade = _EIXO[s.frase][3]
    ini = hoje - timedelta(days=PERIODOS[periodo] - 1)
    ref, aprendendo_texto = _referencia(s, brutos, hoje, unidade)
    no_periodo = _pontos_do_periodo(s, brutos, ini, hoje)
    com_valor = [p for p in no_periodo if p.valor is not None]
    melhor_id = None
    if s.frase in _MELHOR and com_valor:
        escolhido = _MELHOR[s.frase](com_valor, key=lambda p: (p.valor, -p.dia.toordinal()))
        melhor_id = (escolhido.dia, escolhido.atividade_id)
    semana_atual = segunda(hoje)
    normais = _selos(session, [p.atividade_id for p in no_periodo if p.atividade_id is not None])
    pontos: list[PontoOut] = []
    for p in no_periodo:
        texto = None if p.valor is None or p.aprendendo else valor_texto(s.frase, p.valor)
        selo = normais.get(p.atividade_id) if p.atividade_id is not None and p.valor is not None else None
        fora = None if selo in (None, "aprendendo") else selo == "fora"
        data_t = f"semana de {p.dia:%d/%m}" if s.tipo == "volume" else data_texto(p.dia)
        pontos.append(PontoOut(
            p.atividade_id, p.dia, data_t, None if p.valor is None else round(p.valor, 1), texto, melhor_id == (p.dia, p.atividade_id), fora, selo,
            p.aprendendo, s.tipo == "volume" and p.dia == semana_atual, _rotulo_ponto(s, p.dia, data_t, p.valor, texto, fora, unidade)))
    # o último: o treino mais recente com valor; no volume a última semana COMPLETA (a em curso é parcial); no condicionamento, o dia mais recente com número
    candidatos = [p for p in pontos if not p.parcial and p.valor_texto is not None]
    ultimo = candidatos[-1] if candidatos else None
    ultimo_rotulo = None
    if ultimo is not None:
        ultimo_rotulo = (f"semana de {ultimo.data:%d/%m}" if s.tipo == "volume" else
                         f"condicionamento de {data_texto(ultimo.data)}" if s.tipo == "ctl" else f"último treino, {ultimo.data_texto}")
    valores_eixo = [p.valor for p in pontos if p.valor is not None]
    if ref is not None:
        valores_eixo += [ref.minimo, ref.maximo]
    if s.tipo == "volume":
        valores_eixo.append(0.0)
    frase = frase_da_serie(s, brutos, hoje)
    return SerieLida(s, periodo, ini, hoje, unidade, pontos, None if ultimo is None else ultimo.valor_texto, ultimo_rotulo, ref,
                     aprendendo_texto, _eixo(s.frase, valores_eixo), frase, VERSAO)
