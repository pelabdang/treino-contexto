"""Conferência da nossa carga com a carga aguda/crônica do Garmin (issue #144; ADR 0010, item 8).

Função pura: sem banco, sem rede, sem IA. **Só descritiva** (decisão do Angelo, 07/11): não há faixa de aprovação; o resultado
diz o que se observou, sempre com a cobertura. A escala do Garmin é outra, então nunca se compara valor absoluto, só
correlação de postos (Spearman). Regras, exemplo à mão e o que a conferência NÃO prova: docs/metricas/conferencia-carga.md.

Medidas (ADR 0010, item 8), nos dias em que as duas séries existem e nenhuma atividade do dia ficou sem carga:
- níveis: Spearman entre a nossa ATL e a carga aguda do Garmin, e entre a nossa CTL e a crônica;
- diferenças: Spearman das variações dia a dia (x[d] - x[d-1]), só entre dias consecutivos comparados;
- defasagem: o mesmo Spearman dos níveis com o Garmin deslocado de -3 a +3 dias (k > 0: o Garmin em d+k contra a nossa em d);
- razão: nossa ATL/CTL (CTL > 0) contra a razão aguda/crônica do Garmin;
- cobertura: dias de cada série, em comum, descartados e comparados, por medida.

Fonte do Spearman: Spearman, C. (1904), "The proof and measurement of association between two things", Am. J. Psychol.
15(1):72-101; é o coeficiente de Pearson entre os postos, com posto médio nos empates (sem empates:
rho = 1 - 6 x soma(d^2) / (n x (n^2 - 1))). Qualquer mudança de regra exige subir ``VERSAO``.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.metricas.serie_carga import DiaCarga

VERSAO = "conferencia_carga@1"
DEFASAGENS = tuple(range(-3, 4))
MIN_PARES = 3  # abaixo disso o Spearman não é calculado (None)


@dataclass(frozen=True)
class DiaGarmin:
    """Um dia da carga do Garmin (``carga_garmin_dia``). Qualquer campo pode faltar na fonte."""

    dia: date
    aguda: float | None = None
    cronica: float | None = None
    razao: float | None = None


@dataclass(frozen=True)
class Medida:
    grupo: str  # niveis | diferencas | defasagem | razao
    comparacao: str  # atl_aguda | ctl_cronica | razao
    defasagem: int  # dias; 0 fora do grupo defasagem
    n: int  # pares usados
    spearman: float | None  # None: menos de MIN_PARES pares ou uma série constante


@dataclass(frozen=True)
class Cobertura:
    dias_nossa: int
    dias_garmin: int
    dias_em_comum: int
    descartados_sem_carga: int  # em comum, mas com atividade sem carga (se ``descartar_sem_carga``)
    dias_comparados: int


@dataclass(frozen=True)
class Conferencia:
    versao: str
    descartar_sem_carga: bool
    cobertura: Cobertura
    medidas: list[Medida] = field(default_factory=list)

    def medida(self, grupo: str, comparacao: str, defasagem: int = 0) -> Medida:
        for m in self.medidas:
            if (m.grupo, m.comparacao, m.defasagem) == (grupo, comparacao, defasagem):
                return m
        raise KeyError((grupo, comparacao, defasagem))


def _postos(v: Sequence[float]) -> list[float]:
    """Postos de 1 a n, com a média dos postos nos empates."""
    ordem = sorted(range(len(v)), key=lambda i: v[i])
    postos = [0.0] * len(v)
    i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and v[ordem[j + 1]] == v[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            postos[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return postos


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Correlação de Spearman (Pearson dos postos). None com menos de ``MIN_PARES`` pares ou série constante."""
    if len(x) != len(y):
        raise ValueError("séries de tamanhos diferentes")
    n = len(x)
    if n < MIN_PARES:
        return None
    rx, ry = _postos(x), _postos(y)
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def razao_nossa(d: DiaCarga) -> float | None:
    """Nossa ATL/CTL do dia; None com CTL = 0."""
    return d.atl / d.ctl if d.ctl > 0 else None


_COMPARACOES: tuple[tuple[str, Callable[[DiaCarga], float | None], Callable[[DiaGarmin], float | None]], ...] = (
    ("atl_aguda", lambda d: d.atl, lambda g: g.aguda),
    ("ctl_cronica", lambda d: d.ctl, lambda g: g.cronica),
)


def _pares(
    dias_nossa: dict[date, DiaCarga], garmin: dict[date, DiaGarmin], validos: set[date],
    nome: Callable[[DiaCarga], float | None], gar: Callable[[DiaGarmin], float | None], k: int = 0,
) -> list[tuple[float, float]]:
    pares = []
    for d in sorted(validos):
        g = garmin.get(d + timedelta(days=k))
        a, b = nome(dias_nossa[d]), (gar(g) if g else None)
        if a is not None and b is not None:
            pares.append((a, b))
    return pares


def _medida(grupo: str, comp: str, k: int, pares: list[tuple[float, float]]) -> Medida:
    return Medida(grupo, comp, k, len(pares), spearman([a for a, _ in pares], [b for _, b in pares]))


def conferir(
    nossa: Iterable[DiaCarga],
    garmin: Iterable[DiaGarmin],
    descartar_sem_carga: bool = True,
    defasagens: Sequence[int] = DEFASAGENS,
) -> Conferencia:
    """Compara a nossa série diária com a do Garmin. ``descartar_sem_carga=False`` mantém os dias com atividade sem
    carga (natação e ``outra`` nunca têm carga): serve de leitura complementar, com a mesma cobertura declarada."""
    dn = {d.dia: d for d in nossa}
    dg = {g.dia: g for g in garmin}
    em_comum = set(dn) & set(dg)
    # dias válidos do lado da nossa série: sem atividade sem carga (regra da ADR)
    validos_nossa = {d for d, v in dn.items() if not (descartar_sem_carga and v.sem_carga > 0)}
    validos = em_comum & validos_nossa
    cob = Cobertura(len(dn), len(dg), len(em_comum), len(em_comum) - len(validos), len(validos))

    medidas: list[Medida] = []
    for comp, fn, fg in _COMPARACOES:
        medidas.append(_medida("niveis", comp, 0, _pares(dn, dg, validos, fn, fg)))
        # diferenças: só entre dias consecutivos, ambos comparados e com valor nas duas séries
        difs = []
        for d in sorted(validos):
            ant = d - timedelta(days=1)
            if ant not in validos:
                continue
            a1, a0 = fn(dn[d]), fn(dn[ant])
            b1, b0 = fg(dg[d]), fg(dg[ant])
            if None not in (a1, a0, b1, b0):
                difs.append((a1 - a0, b1 - b0))
        medidas.append(_medida("diferencas", comp, 0, difs))
        for k in defasagens:
            # nossa em d (válido) contra o Garmin em d + k
            medidas.append(_medida("defasagem", comp, k, _pares(dn, dg, validos_nossa & set(dn), fn, fg, k)))
    razoes = []
    for d in sorted(validos):
        a, b = razao_nossa(dn[d]), dg[d].razao
        if a is not None and b is not None:
            razoes.append((a, b))
    medidas.append(_medida("razao", "razao", 0, razoes))
    return Conferencia(VERSAO, descartar_sem_carga, cob, medidas)
