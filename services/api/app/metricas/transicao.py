"""Treino de transição (brick): regra que sugere o rótulo (issue #156, ADR 0009).

Função pura: sem banco, sem rede, sem IA. A regra completa, os exemplos e as
limitações estão em docs/metricas/transicao.md. Qualquer mudança de regra ou de
constante exige subir ``VERSAO`` (gravada junto do rótulo sugerido).

Fonte: regra própria do projeto (não há artigo); decisão do Angelo de 04/11 e 06/11
(ADR 0009). Duas atividades seguidas de modalidades diferentes, coladas no tempo,
formam um par de transição.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

VERSAO = "transicao@1"

MODALIDADES_DE_TRANSICAO = frozenset({"corrida", "natacao", "ciclismo"})
# Intervalo estimado máximo entre o maior fim já visto e o início seguinte
# (decisão do Angelo, 06/11).
INTERVALO_MAX_S = 1800
# Sobreposição tolerada (relógio abre a parte seguinte antes de fechar a anterior;
# resolução de 1 s dos horários).
SOBREPOSICAO_MAX_S = 60


@dataclass(frozen=True)
class AtividadeLeve:
    id: int
    modalidade: str
    inicio: datetime  # com fuso (UTC)
    duracao_s: float  # tempo em movimento; o fim é estimado por inicio + duracao_s


def sugerir_transicao(atividades: Iterable[AtividadeLeve]) -> set[int]:
    """Devolve os ``id`` das atividades sugeridas como treino de transição.

    Entram só atividades com modalidade em ``MODALIDADES_DE_TRANSICAO``; ``outra`` fica
    fora e não interrompe a vizinhança das demais. Ordena por ``inicio`` (desempate por
    ``id``). Cada atividade é comparada com o **maior fim já visto** entre as anteriores
    (e não só com a vizinha imediata), de modo que uma atividade aninhada ou duplicada não
    esconde a transição real. O par é formado com a(s) atividade(s) que têm esse maior
    fim, se a modalidade for diferente e o intervalo ``inicio - maior_fim`` ficar entre
    ``-SOBREPOSICAO_MAX_S`` e ``INTERVALO_MAX_S``. Uma atividade em dois pares entra uma
    vez só. Só sugere "sim": quem não está no resultado fica sem rótulo.
    """
    elegiveis = sorted(
        (a for a in atividades if a.modalidade in MODALIDADES_DE_TRANSICAO),
        key=lambda a: (a.inicio, a.id),
    )
    sugeridas: set[int] = set()
    maior_fim: datetime | None = None
    donas_do_fim: list[AtividadeLeve] = []
    for atual in elegiveis:
        if maior_fim is not None:
            intervalo = (atual.inicio - maior_fim).total_seconds()
            if -SOBREPOSICAO_MAX_S <= intervalo <= INTERVALO_MAX_S:
                for dona in donas_do_fim:
                    if dona.modalidade != atual.modalidade:
                        sugeridas.add(dona.id)
                        sugeridas.add(atual.id)
        fim = atual.inicio + timedelta(seconds=max(atual.duracao_s, 0))
        if maior_fim is None or fim > maior_fim:
            maior_fim = fim
            donas_do_fim = [atual]
        elif fim == maior_fim:
            donas_do_fim.append(atual)
    return sugeridas
