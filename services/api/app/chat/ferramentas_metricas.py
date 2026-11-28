"""Ferramentas do chat sobre as métricas (#594, ADR 0017, item 1): `ler_serie`, `comparar_periodos`, `ler_carga_forma`, `ler_linha_base`, `ler_recuperacao`.

Só registram, no registro da #593, as funções puras de `app.explicacao.ferramentas_chat` (nenhuma métrica nova). O `atleta_id` vem da `Consulta`,
nunca dos argumentos; o "hoje" da `Consulta` vira o relógio das funções. A Evolução (`ler_serie` e `comparar_periodos`) é só do atleta: o professor
não a vê (decisão 7 do Angelo, 28/11). Dado de saúde: nada daqui vai para log.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.chat import periodo as per
from app.chat.registro import Consulta, registrar
from app.db.models import TIPOS_TREINO
from app.explicacao import ferramentas_chat as fc
from app.servicos.evolucao_series import POR_ID

MODALIDADES = ("corrida", "natacao", "ciclismo")
_SERIE = {"type": "string", "enum": sorted(POR_ID), "description": "id de uma série do catálogo da Evolução (por exemplo `corrida.pace.leve`)"}
_PERIODO = {"type": "string", "enum": list(fc.PERIODOS_DIAS), "description": "janela pronta, contada a partir de hoje (data local do atleta)"}
_DE = {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}", "description": "início AAAA-MM-DD; use com `ate`, sem `periodo`"}
_ATE = {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}", "description": "fim AAAA-MM-DD; use com `de`, sem `periodo`"}
_PERIODO_COMPARAR = {"type": "string", "maxLength": 40, "pattern": "|".join([*fc.PERIODOS_COMPARAVEIS, r"\d{4}-\d{2}"]),
                     "description": ("um dos nomes (" + ", ".join(fc.PERIODOS_COMPARAVEIS) + ") ou um mês `AAAA-MM`; os dois lados têm o mesmo tamanho")}


def _agora(c: Consulta) -> datetime:
    """O relógio das funções: meio-dia UTC do "hoje" da consulta (o `hoje` do atleta sai igual em qualquer fuso do Brasil)."""
    return datetime.combine(c.hoje, time(12, 0), tzinfo=timezone.utc)


@registrar(
    "ler_serie",
    "Lê uma série da Evolução (pace, FC, volume, condicionamento, tiros...) num período: os pontos com valor em texto pronto, o último valor, a faixa do "
    "normal do atleta e a frase de 4 semanas. Só do atleta.",
    {"serie_id": _SERIE, "periodo": _PERIODO, "de": _DE, "ate": _ATE},
    ("atleta",),
    ("serie_id",),
)
def ler_serie(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return fc.serie_evolucao(session, c.atleta_id, a["serie_id"], a.get("periodo"), a.get("de"), a.get("ate"), _agora(c))


@registrar(
    "comparar_periodos",
    "Compara uma série da Evolução entre dois períodos de mesmo tamanho (semana, 14 ou 28 dias, 12 semanas, semana ou mês de calendário): o valor e o número "
    "de treinos de cada um, a direção (maior, menor, parecido), a diferença e a margem, tudo calculado pelo código. Sem os dois períodos, compara os últimos "
    "28 dias com os 28 anteriores. Só do atleta.",
    {"serie_id": _SERIE, "periodo_a": _PERIODO_COMPARAR, "periodo_b": _PERIODO_COMPARAR},
    ("atleta",),
    ("serie_id",),
)
def comparar_periodos(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return fc.comparar_periodos(session, c.atleta_id, a["serie_id"], a.get("periodo_a", fc.PAR_DA_COMPARACAO[0]), a.get("periodo_b", fc.PAR_DA_COMPARACAO[1]), _agora(c))


@registrar(
    "ler_carga_forma",
    "Lê a carga e a forma de um dia: CTL, ATL e TSB (estimativas) e a frase da forma. A série vai até ontem; sem `data`, vale o último dia calculado.",
    {"data": {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}", "description": "dia AAAA-MM-DD"}},
    ("atleta", "professor"),
)
def ler_carga_forma(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return fc.carga_e_forma(session, c.atleta_id, a.get("data"), _agora(c))


@registrar(
    "ler_linha_base",
    "Lê o normal do atleta para um tipo de treino (modalidade e tipo): a mediana de cada métrica na janela de 12 semanas, o número de treinos e o estado.",
    {"modalidade": {"type": "string", "enum": list(MODALIDADES)}, "tipo_treino": {"type": "string", "enum": list(TIPOS_TREINO)}},
    ("atleta", "professor"),
    ("modalidade", "tipo_treino"),
)
def ler_linha_base(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return fc.linha_base(session, c.atleta_id, a["modalidade"], a["tipo_treino"])


@registrar(
    "ler_recuperacao",
    "Lê o sono, a VFC e a FC de repouso de cada noite de um período (padrão: últimos 7 dias) contra o normal do atleta, em texto pronto: abaixo e acima são só "
    "direção, nunca bom ou ruim. Só do atleta.",
    {"periodo": _PERIODO, "de": _DE, "ate": _ATE},
    ("atleta",),
)
def ler_recuperacao(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return fc.recuperacao_noites(session, c.atleta_id, a.get("periodo"), a.get("de"), a.get("ate"), _agora(c))
