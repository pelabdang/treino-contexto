"""Linha de base pessoal e desvio robusto (issue #263, ADR 0011).

Função pura: sem banco, sem rede, sem IA. Regra, exemplos e limites em docs/metricas/linha-base.md. Qualquer mudança de
janela, mínimo, medida, limite, condições de entrada ou lista de métricas exige subir ``VERSAO``.

Fórmulas e fontes:
  mediana = mediana(x) ;  MAD = mediana(|x_i - mediana|) ;
  desvio = max(1,4826 x MAD, PISO_REL x |mediana|) ;  z = (valor - mediana) / desvio ; "fora" quando |z| >= LIMITE_FORA.
  Mediana e MAD no lugar de média e desvio padrão: Leys, C. et al. (2013), "Detecting outliers: do not use standard
  deviation around the mean, use absolute deviation around the median", J. Exp. Soc. Psychol. 49(4):764-766 (limite 2,5
  "moderadamente conservador"). Constante 1,4826: Rousseeuw, P. J. e Croux, C. (1993), JASA 88(424):1273-1283.
  (Citações ainda a conferir nos textos, ADR 0011 "Fontes".) O piso de 2% da mediana, a janela e o mínimo de 8 treinos
  são regra própria do projeto (Angelo, 09/11). ``linha_base@2`` (Angelo, 09/11, issue #288, adendo 2 da ADR 0011): janela de
  12 semanas, partes de treino de transição com base própria e carga por hora no lugar da carga absoluta.
"""

from __future__ import annotations

import statistics
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

VERSAO = "linha_base@2"


@dataclass(frozen=True)
class Parametros:
    janela_dias: int = 84  # 12 semanas (@2; era 56 na @1)
    minimo_treinos: int = 8  # (Angelo, 09/11)
    limite_fora: float = 2.5  # ADR 0011 "A confirmar" 3
    piso_rel: float = 0.02  # calibração #269
    mad_escala: float = 1.4826
    divergente_fora_da_base: bool = True  # "A confirmar" 2


PADRAO = Parametros()

SUBTIPOS_MULTIESPORTE = frozenset({"multiesporte_pai", "troca"})

# Métricas por modalidade e tipo (ADR 0011, item 7). Corrida depende do tipo; ciclismo e natação, não.
_CORRIDA = {
    "intervalado": ("melhor_pace", "fc_melhor_tiro", "fc_media", "carga_hora"),
    "leve": ("pace_medio", "fc_media", "carga_hora"),
    "longo": ("pace_medio", "fc_media", "carga_hora"),
    "moderado": ("pace_medio", "fc_media", "carga_hora"),
    "fartlek": ("fc_media", "carga_hora"),
}
_CICLISMO = ("fc_media", "carga_hora")
_NATACAO = ("fc_media",)


def metricas_do_tipo(modalidade: str, tipo_treino: str | None) -> tuple[str, ...]:
    if modalidade == "corrida":
        return _CORRIDA.get(tipo_treino or "", ())
    if modalidade == "ciclismo":
        return _CICLISMO
    if modalidade == "natacao":
        return _NATACAO
    return ()


@dataclass(frozen=True)
class Treino:
    """O que a função precisa de uma atividade; os valores (pace, FC, carga) são calculados por quem chama."""

    id: Hashable
    inicio: datetime  # instante (com fuso); a ordem "anterior à sessão" é por ele
    dia: date  # data local (ADR 0003); a janela é por ele
    modalidade: str
    tipo_treino: str | None
    valores: Mapping[str, float | None] = field(default_factory=dict)  # chave da métrica -> valor (None = sem o dado)
    subtipo: str | None = None
    divergente: bool = False
    transicao: bool = False


@dataclass(frozen=True)
class MetricaBase:
    chave: str
    estado: str  # fora | dentro | aprendendo | sem_valor
    valor: float | None
    n: int  # quantos treinos da janela têm a métrica
    mediana: float | None = None
    desvio: float | None = None
    z: float | None = None


@dataclass(frozen=True)
class LinhaBase:
    versao: str
    estado: str  # ok | sem_linha_base
    motivo: str | None
    metricas: tuple[MetricaBase, ...]


def motivo_sem_linha_base(t: Treino, p: Parametros = PADRAO) -> str | None:
    """Primeiro motivo da ordem da ADR 0011 (item 7): multiesporte, modalidade_sem_metricas, sem_tipo, divergente.

    Na ``linha_base@2`` a parte de treino de transição não é motivo: tem base própria (``linha_base``)."""
    if t.subtipo in SUBTIPOS_MULTIESPORTE:
        return "multiesporte"
    if t.modalidade == "outra":
        return "modalidade_sem_metricas"
    if t.tipo_treino is None:
        return "sem_tipo"
    if p.divergente_fora_da_base and t.divergente:
        return "divergente"
    return None


def medida_robusta(valores: Sequence[float], p: Parametros = PADRAO) -> tuple[float, float]:
    """(mediana, desvio) com o piso; precisa de ao menos um valor."""
    mediana = statistics.median(valores)
    mad = statistics.median(abs(x - mediana) for x in valores)
    return mediana, max(p.mad_escala * mad, p.piso_rel * abs(mediana))


def _metrica(chave: str, valor: float | None, janela: Sequence[float], p: Parametros) -> MetricaBase:
    n = len(janela)
    if valor is None:
        return MetricaBase(chave, "sem_valor", None, n)
    if n < p.minimo_treinos:
        return MetricaBase(chave, "aprendendo", valor, n)
    mediana, desvio = medida_robusta(janela, p)
    z = (valor - mediana) / desvio
    return MetricaBase(chave, "fora" if abs(z) >= p.limite_fora else "dentro", valor, n, mediana, desvio, z)


def linha_base(sessao: Treino, historico: Sequence[Treino], p: Parametros = PADRAO) -> LinhaBase:
    """Linha de base de cada métrica do tipo da sessão (ADR 0011, item 6).

    Entram na janela: mesma modalidade e mesmo tipo; **mesmo grupo** (parte de transição só com parte de transição,
    isolada só com isolada, ``Treino.transicao``); ``inicio`` anterior ao da sessão; data local de ``sessao.dia - janela_dias``
    em diante; sem motivo para ficar fora da base (``motivo_sem_linha_base``). A sessão nunca entra na própria linha de base
    (mesmo ``id``, ou ``inicio`` igual ou posterior). Cada métrica conta só os treinos que têm o valor.
    """
    motivo = motivo_sem_linha_base(sessao, p)
    if motivo is not None:
        return LinhaBase(VERSAO, "sem_linha_base", motivo, ())
    desde = sessao.dia - timedelta(days=p.janela_dias)
    janela = [
        t for t in historico
        if t.id != sessao.id and t.modalidade == sessao.modalidade and t.tipo_treino == sessao.tipo_treino
        and t.transicao == sessao.transicao
        and t.inicio < sessao.inicio and t.dia >= desde and motivo_sem_linha_base(t, p) is None
    ]
    metricas = []
    for chave in metricas_do_tipo(sessao.modalidade, sessao.tipo_treino):
        xs = [v for v in (t.valores.get(chave) for t in janela) if v is not None]
        metricas.append(_metrica(chave, sessao.valores.get(chave), xs, p))
    return LinhaBase(VERSAO, "ok", None, tuple(metricas))
