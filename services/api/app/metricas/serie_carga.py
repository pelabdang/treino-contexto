"""CTL, ATL e TSB diários a partir da carga por dia (issue #139, ADR 0010 item 6).

Função pura: sem banco, sem rede, sem IA. Regras, exemplo à mão e limitações em
docs/metricas/serie-carga.md. Qualquer mudança de regra ou constante exige subir ``VERSAO``.

Fontes: modelo de impulso-resposta de Banister, Calvert, Savage e Bach, IEEE Trans. Syst. Man
Cybern. SMC-6(2):94-102, 1976; Performance Management Chart do TrainingPeaks (janelas de 42 e 7
dias); forma exata ``1 - exp(-1/tau)`` da planilha do Golden Cheetah. Diferença para o
TrainingPeaks: o TSB aqui é CTL - ATL do fim do mesmo dia (glossário), não o do dia anterior.

Entrada: atividades já com o dia LOCAL (``app.servicos.fuso.data_local``, ADR 0003); a conversão
fica com quem chama, para esta função não depender de fuso. Atividades multiesporte_pai e troca
não entram: o chamador passa só a contagem delas em ``ignoradas_multiesporte``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta

VERSAO = "serie_carga@1"

TAU_CTL = 42
TAU_ATL = 7
K_CTL = 1 - math.exp(-1 / TAU_CTL)
K_ATL = 1 - math.exp(-1 / TAU_ATL)
# "Ainda aprendendo": menos de 42 dias desde o primeiro dia da série (ADR 0010, item 6).
DIAS_APRENDENDO = 42

MOTIVOS = (
    "sem_dados_saude",
    "sem_limiar_na_data",
    "sem_fc",
    "sem_pace",
    "cobertura_insuficiente",
    "modalidade_sem_carga",
)


@dataclass(frozen=True)
class AtividadeCarga:
    """Uma atividade elegível. ``carga`` None = sem carga, e então ``motivo`` é um de ``MOTIVOS``."""

    dia: date
    carga: float | None = None
    motivo: str | None = None

    def __post_init__(self) -> None:
        if self.carga is None and self.motivo not in MOTIVOS:
            raise ValueError(f"atividade sem carga precisa de motivo válido, veio {self.motivo!r}")
        if self.carga is not None and self.motivo is not None:
            raise ValueError("atividade com carga não tem motivo")
        if self.carga is not None and self.carga < 0:
            raise ValueError("carga negativa")


@dataclass(frozen=True)
class DiaCarga:
    dia: date
    carga: float  # L_d: soma das cargas calculadas do dia
    ctl: float
    atl: float
    tsb: float  # ctl - atl, do mesmo dia
    aprendendo: bool
    atividades: int
    calculadas: int
    sem_carga: int


@dataclass(frozen=True)
class TotaisCarga:
    calculadas: int
    sem_carga_total: int
    por_motivo: dict[str, int]
    ignoradas_multiesporte: int


@dataclass(frozen=True)
class SerieCarga:
    versao: str
    dias: list[DiaCarga] = field(default_factory=list)
    totais: TotaisCarga | None = None


def calcular_serie(atividades: Iterable[AtividadeCarga], ignoradas_multiesporte: int = 0) -> SerieCarga:
    """Série diária do primeiro dia com carga calculada até o dia da última atividade.

    Sem nenhuma carga calculada, ``dias`` é vazio (não há primeiro dia) e os totais continuam.
    Os totais contam todas as atividades recebidas, inclusive as anteriores ao início da série.
    """
    lista = list(atividades)
    calculadas = [a for a in lista if a.carga is not None]
    sem_carga = [a for a in lista if a.carga is None]
    por_motivo = {m: 0 for m in MOTIVOS}
    for a in sem_carga:
        por_motivo[a.motivo] += 1  # type: ignore[index]
    totais = TotaisCarga(len(calculadas), len(sem_carga), por_motivo, ignoradas_multiesporte)
    if not calculadas:
        return SerieCarga(VERSAO, [], totais)

    por_dia: dict[date, list[AtividadeCarga]] = {}
    for a in lista:
        por_dia.setdefault(a.dia, []).append(a)

    primeiro = min(a.dia for a in calculadas)
    ultimo = max(a.dia for a in lista)
    ctl = atl = 0.0  # semente: zero antes do primeiro dia com carga
    dias: list[DiaCarga] = []
    dia = primeiro
    while dia <= ultimo:
        do_dia = por_dia.get(dia, [])
        carga = sum(a.carga for a in do_dia if a.carga is not None)
        ctl += (carga - ctl) * K_CTL
        atl += (carga - atl) * K_ATL
        n_calc = sum(a.carga is not None for a in do_dia)
        dias.append(
            DiaCarga(
                dia=dia,
                carga=carga,
                ctl=ctl,
                atl=atl,
                tsb=ctl - atl,
                aprendendo=(dia - primeiro).days < DIAS_APRENDENDO,
                atividades=len(do_dia),
                calculadas=n_calc,
                sem_carga=len(do_dia) - n_calc,
            )
        )
        dia += timedelta(days=1)
    return SerieCarga(VERSAO, dias, totais)
