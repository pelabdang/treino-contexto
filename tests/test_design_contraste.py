"""Confere o contraste do guia visual (issue #192; docs/design/tokens.md).

O script docs/design/contraste.py lê as cores de tokens.md e escreve a tabela de contraste. Aqui conferimos a
fórmula com valores conhecidos da WCAG, que todo par passa no mínimo AA e que a tabela da nota não está velha.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "docs" / "design" / "contraste.py"


@pytest.fixture(scope="module")
def contraste():
    spec = importlib.util.spec_from_file_location("contraste_design", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_formula_com_valores_conhecidos(contraste):
    assert contraste.razao("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contraste.razao("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    # #767676 sobre branco é o cinza mais claro que passa 4,5 (valor de referência conhecido: 4,54).
    assert contraste.razao("#767676", "#FFFFFF") == pytest.approx(4.54, abs=0.01)
    # A ordem dos argumentos não muda a razão.
    assert contraste.razao("#0B6A6E", "#F6F5F1") == contraste.razao("#F6F5F1", "#0B6A6E")


def test_todo_par_passa_no_minimo_aa(contraste):
    linhas = contraste.calcular(contraste.ler_cores(contraste.TOKENS.read_text(encoding="utf-8")))
    falhas = [(l["frente"], l["fundo"], round(l["claro"], 2), round(l["escuro"], 2)) for l in linhas if not l["ok"]]
    assert falhas == []


def test_todo_token_dos_pares_tem_cor(contraste):
    cores = contraste.ler_cores(contraste.TOKENS.read_text(encoding="utf-8"))
    usados = {t for frente, fundo, _ in contraste.PARES for t in (frente, fundo)}
    assert usados <= set(cores)


def test_tabela_da_nota_esta_atualizada(contraste):
    texto = contraste.TOKENS.read_text(encoding="utf-8")
    assert contraste.documento_atualizado(texto) == texto, "rode: python docs/design/contraste.py --escrever"
