"""Testes do selo por treino (issue #551). Esperados à mão a partir da regra: fora > dentro > aprendendo > None."""

import pytest

from app.metricas.normal_treino import VERSAO, normal_treino


def test_versao():
    assert VERSAO == "normal_treino@1"


@pytest.mark.parametrize(
    ("estados", "esperado"),
    [
        (["fora"], "fora"),  # uma só fora basta
        (["dentro", "fora", "dentro"], "fora"),  # fora vence dentro
        (["aprendendo", "fora"], "fora"),
        (["dentro", "dentro"], "dentro"),
        (["dentro", "aprendendo"], "dentro"),  # dentro + aprendendo dá dentro
        (["sem_valor", "dentro"], "dentro"),
        (["aprendendo", "aprendendo"], "aprendendo"),
        (["sem_valor", "aprendendo"], "aprendendo"),
        (["sem_valor", "sem_valor"], None),  # tudo sem valor
        ([], None),  # sem métricas
    ],
)
def test_agregacao_com_linha_de_base_ok(estados, esperado):
    assert normal_treino("ok", estados) == esperado


@pytest.mark.parametrize("estados", [[], ["fora"], ["dentro"], ["aprendendo"]])
def test_sem_linha_base_e_none(estados):
    assert normal_treino("sem_linha_base", estados) is None


def test_aceita_qualquer_iteravel():
    assert normal_treino("ok", (e for e in ["dentro", "fora"])) == "fora"
