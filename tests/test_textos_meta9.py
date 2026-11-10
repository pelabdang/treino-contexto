"""Textos bons e ruins das checagens do feedback (issue #323, parte 2): confere a lista, não as checagens.

As checagens (#325) é que decidem se cada texto passa ou reprova; aqui só se garante que a lista é sólida: os 6 primeiros bons são os
exemplos da ADR 0013 palavra por palavra, cada ruim tem um motivo de um conjunto fechado e cobre o que a issue pede, e nenhum texto
carrega dado pessoal. Tudo sintético.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

PASTA = Path(__file__).parent / "fixtures" / "meta9"
RAIZ = Path(__file__).parent.parent


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(f"{nome}_meta9", PASTA / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


T = _carregar("textos")
O = _carregar("oraculo")


def _linhas(texto):
    return [x for x in texto.split("\n") if x.strip()]


def _exemplos_da_adr():
    """Os 'Texto esperado' dos exemplos 1 a 6 da ADR 0013, na ordem."""
    adr = (RAIZ / "docs" / "decisoes" / "0013-feedback-automatico.md").read_text(encoding="utf-8")
    blocos = re.findall(r"\*\*Texto esperado\*\*\n((?:>.*\n?)+)", adr)
    return ["\n".join(linha[1:].strip() for linha in b.strip().split("\n")) for b in blocos]


def test_os_seis_primeiros_bons_sao_os_exemplos_da_adr():
    exemplos = _exemplos_da_adr()
    assert len(exemplos) == 6
    for k, exemplo in enumerate(exemplos, start=1):
        caso, texto = T.BONS[f"G0{k}"]
        assert texto == exemplo, f"G0{k}"
        assert caso == f"F0{k}"


def test_cada_caso_tem_pacote():
    for caso, _texto in T.BONS.values():
        assert O.PACOTES[caso] is not None, caso
    for caso, _texto, _m, _p in T.RUINS.values():
        assert O.PACOTES[caso] is not None, caso


def test_bons_tem_de_3_a_5_linhas_de_ate_140_caracteres():
    for i, (_c, texto) in T.BONS.items():
        ls = _linhas(texto)
        assert 3 <= len(ls) <= 5, i
        assert all(len(x) <= 140 for x in ls), i


def test_motivos_sao_de_um_conjunto_fechado_e_sem_repeticao():
    assert len(set(T.MOTIVOS)) == len(T.MOTIVOS)
    for i, (_c, _t, motivo, porque) in T.RUINS.items():
        assert motivo in T.MOTIVOS, i
        assert porque.strip(), i


def test_ruins_cobrem_tudo_o_que_a_issue_pede():
    usados = {m for (_c, _t, m, _p) in T.RUINS.values()}
    pedidos = {"numero_fora_do_pacote", "linguagem_diagnostico", "linguagem_culpa", "linguagem_promessa", "linguagem_causa",
               "linguagem_conselho", "elogio_sem_fato", "dor_regra", "numero_por_extenso", "unidade_trocada", "linguagem_quem_fala"}
    assert pedidos <= usados
    assert usados == set(T.MOTIVOS)  # nenhum código sem exemplo ruim


def test_conselho_sobre_dor_esta_na_lista():
    assert any(c == "F05" and "dor" in t and m == "linguagem_conselho" for (c, t, m, _p) in T.RUINS.values())


def test_um_ruim_nao_e_igual_a_um_bom_nem_a_outro_ruim():
    bons = {t for _c, t in T.BONS.values()}
    ruins = [t for _c, t, _m, _p in T.RUINS.values()]
    assert not bons & set(ruins)
    assert len(set(ruins)) == len(ruins)


@pytest.mark.parametrize("texto", [t for _c, t in T.BONS.values()] + [t for _c, t, _m, _p in T.RUINS.values()])
def test_nenhum_texto_leva_dado_pessoal(texto):
    # o marcador do texto livre só aparece no ruim que o repete de propósito (R39); a data só no R04
    if O.MARCADOR_TEXTO_LIVRE in texto:
        assert texto == T.RUINS["R39"][1]
    if "2026" in texto:
        assert texto == T.RUINS["R04"][1]
    assert not re.search(r"@|https?://", texto)
