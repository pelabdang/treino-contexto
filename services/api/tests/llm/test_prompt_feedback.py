"""Prompt `feedback_prompt@2` e seus 6 exemplos (issue #327, revisão do Caio no PR #348): fonte única conferida contra as fixtures da meta 9."""

import importlib.util
import sys
from pathlib import Path

import pytest
from app.explicacao import checagens
from app.llm import prompt_feedback
from app.llm.exemplos_feedback import EXEMPLOS

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9"


def _carrega(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, PASTA / arquivo)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


O = _carrega("oraculo_meta9_prompt", "oraculo.py")
T = _carrega("textos_meta9_prompt", "textos.py")


def _contido(parte, todo) -> bool:
    """`parte` esta em `todo`: mesmos valores nas chaves que `parte` tem (listas elemento a elemento)."""
    if isinstance(parte, dict):
        return isinstance(todo, dict) and all(k in todo and _contido(v, todo[k]) for k, v in parte.items())
    if isinstance(parte, list):
        return isinstance(todo, list) and len(parte) == len(todo) and all(_contido(a, b) for a, b in zip(parte, todo))
    return parte == todo


def test_sao_os_6_exemplos_da_adr_g01_a_g06():
    assert [e["id"] for e in EXEMPLOS] == ["G01", "G02", "G03", "G04", "G05", "G06"]


@pytest.mark.parametrize("e", EXEMPLOS, ids=[e["id"] for e in EXEMPLOS])
def test_texto_do_exemplo_e_identico_ao_das_fixtures(e):
    caso, texto = T.BONS[e["id"]]
    assert (e["caso"], e["texto"]) == (caso, texto)


@pytest.mark.parametrize("e", EXEMPLOS, ids=[e["id"] for e in EXEMPLOS])
def test_pacote_reduzido_esta_contido_no_do_oraculo(e):
    assert _contido(e["pacote"], O.PACOTES[e["caso"]])


@pytest.mark.parametrize("e", EXEMPLOS, ids=[e["id"] for e in EXEMPLOS])
def test_o_exemplo_passa_nas_checagens_contra_o_pacote_completo(e):
    assert checagens.checar(O.PACOTES[e["caso"]], e["texto"]) is None


def test_os_seis_exemplos_estao_no_prompt_e_o_prompt_nao_tem_dado():
    for e in EXEMPLOS:
        assert e["texto"] in prompt_feedback.TEXTO
    assert O.MARCADOR_TEXTO_LIVRE not in prompt_feedback.TEXTO
    assert prompt_feedback.VERSAO == "feedback_prompt@2"


def test_prompt_com_acentos_e_sem_a_ortografia_sem_acento():
    t = prompt_feedback._REGRAS  # as chaves do pacote nos exemplos (`cansaco`) ficam sem acento por definicao
    for com in ("Você", "português", "número", "cansaço", "observação"):
        assert com in t
    for sem in ("Voce ", "numero ", "cansaco", "observacao"):
        assert sem not in t


@pytest.mark.parametrize("trecho", [
    '"ruim"', "sono ruim", "ótimo", "parabéns", "excelente",  # elogio sem fato
    "por extenso", "dobro", "metade",  # numero por extenso
    "unidade", '"5:44/km" não vira "5:44 bpm"',  # unidade do *_texto
    "aprendendo", "sem_linha_base", "sem_carga", "pendente", "indoor",  # estados sem valor
    "sozinha na linha", "Você registrou dor neste treino.",  # dor
    "nós", "eu, meu",  # primeira pessoa
    "verbo conjugado", "valor_texto", "mediana_texto", "Não repita a mesma conclusão sobre a mesma coisa", 'Nunca escreva "dentro da mediana"', "Escolha o essencial", "sem \"pois\"", 'nunca "seu FC médio"',  # forma (@2, #355)
])
def test_prompt_traz_os_avisos_pedidos(trecho):
    assert trecho in prompt_feedback.TEXTO


def test_tamanho_do_prompt_cabe_no_limite_de_tokens():
    """Estimativa grosseira (4 caracteres por token): prompt + pacote precisam caber com folga em 8.000 tokens por minuto."""
    assert len(prompt_feedback.TEXTO) / 4 < 3500
