"""`checagens_feedback@6` (issue #405): o que o texto diz do clima bate com `clima.estado`. Textos em `tests/fixtures/meta10/textos_clima.py`."""

import importlib.util
import sys
from pathlib import Path

import pytest
from app.explicacao import checagens as ck

PASTA = Path(__file__).parents[4] / "tests" / "fixtures"


def _carregar(subpasta, arquivo, nome):
    spec = importlib.util.spec_from_file_location(nome, PASTA / subpasta / arquivo)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


O9 = _carregar("meta9", "oraculo.py", "oraculo_meta9_checagens_clima")
T = _carregar("meta10", "textos_clima.py", "textos_meta10_clima")


def _pacote(estado):
    return {**O9.PACOTES["F01"], "clima": T.CLIMAS[estado]}


@pytest.mark.parametrize("i", list(T.BONS))
def test_texto_bom_passa(i):
    estado, texto = T.BONS[i]
    assert ck.checar_texto(_pacote(estado), texto).motivos == ()


@pytest.mark.parametrize("i", list(T.RUINS))
def test_texto_ruim_reprova_com_o_motivo_certo(i):
    estado, texto, motivo = T.RUINS[i]
    assert motivo in ck.checar_texto(_pacote(estado), texto).motivos


def test_natacao_sem_bloco_de_clima_nao_aceita_temperatura_nem_estado():
    pacote = {**O9.PACOTES["F01"], "clima": None}
    assert "clima_estado" in ck.checar_texto(pacote, "\n".join([T.L1, T.L2, T.CK, "O clima ainda está pendente."])).motivos
    assert "clima_estado" in ck.checar_texto(pacote, "\n".join([T.L1, T.L2, T.CK, "Foram 47 min a 19 °C."])).motivos
    assert "clima_estado" not in ck.checar_texto(pacote, "\n".join([T.L1, T.L2, T.CK])).motivos


def test_indoor_so_conta_quando_preso_a_clima():
    # "indoor" descrevendo o treino não é palavra de estado do clima, mesmo com o clima pendente na frase seguinte
    pacote = _pacote("pendente")
    texto = "\n".join([T.L1, T.L2, T.CK, "Foram 47 min no treino indoor. O clima ainda está pendente."])
    assert "clima_estado" not in ck.checar_texto(pacote, texto).motivos
