"""Bloco `recuperacao` do `fatos_treino@2` (issue #374, ADR 0014, item 4). Oráculo à mão em
`tests/fixtures/meta10/oraculo_fatos_recuperacao.py`; tudo sintético."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from app.explicacao import fatos_treino as ft
from app.metricas import recuperacao as rc

PASTA = Path(__file__).parents[4] / "tests" / "fixtures"


def _carregar(subpasta, arquivo, nome):
    spec = importlib.util.spec_from_file_location(nome, PASTA / subpasta / arquivo)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


R = _carregar("meta10", "oraculo_fatos_recuperacao.py", "oraculo_meta10_fatos_rec")


def _recuperacao(caso):
    noites = [rc.Noite(n["noite"], n["sono_s"], n["vfc_ms"], n["fc_repouso_bpm"]) for n in caso["noites"]]
    return rc.recuperacao(caso["dia"], caso["hora"], noites)


@pytest.mark.parametrize("i", list(R.CASOS))
def test_bloco_igual_ao_oraculo(i):
    assert ft._recuperacao(_recuperacao(R.CASOS[i])) == R.CASOS[i]["bloco"]


@pytest.mark.parametrize("i", list(R.CASOS))
def test_so_as_chaves_da_adr(i):
    b = ft._recuperacao(_recuperacao(R.CASOS[i]))
    assert tuple(b) == (R.CHAVES_BLOCO_OK if b["estado"] == "ok" else R.CHAVES_BLOCO_SEM_DADO)
    for m in b.get("medidas", ()):
        assert tuple(m) == R.CHAVES_MEDIDA


def test_sem_recuperacao_o_bloco_e_none():
    assert ft._recuperacao(None) is None


def test_ordem_das_medidas():
    b = ft._recuperacao(_recuperacao(R.CASOS["R01"]))
    assert [m["chave"] for m in b["medidas"]] == ["sono", "vfc", "fc_repouso"]


def test_a_diferenca_fecha_a_conta_dos_textos_arredondados():
    sono = ft._recuperacao(_recuperacao(R.CASOS["R03"]))["medidas"][0]
    assert (sono["valor_texto"], sono["normal_texto"], sono["diferenca_texto"]) == ("6 h", "7 h 16 min", "1 h 16 min abaixo")


def test_hm():
    assert [ft._hm(s) for s in (45 * 60, 3600, 5 * 3600 + 40 * 60, 6 * 3600, 29)] == ["45 min", "1 h", "5 h 40 min", "6 h", "0 min"]


def test_pacote_completo_leva_o_bloco_depois_do_clima_e_o_resto_nao_muda():
    spec = importlib.util.spec_from_file_location("test_fatos_treino_base", Path(__file__).parent / "test_fatos_treino.py")
    base = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base
    spec.loader.exec_module(base)
    _pacote = base._pacote

    sem = _pacote("F01")
    com = _pacote("F01", recuperacao=_recuperacao(R.CASOS["R01"]))
    assert tuple(com) == tuple(sem) and tuple(com).index("recuperacao") == tuple(com).index("clima") + 1
    assert com["recuperacao"] == R.CASOS["R01"]["bloco"]
    assert {k: v for k, v in com.items() if k != "recuperacao"} == {k: v for k, v in sem.items() if k != "recuperacao"}
    assert sem["recuperacao"] is None


def test_nao_vaza_data_nem_serie():
    texto = json.dumps(ft._recuperacao(_recuperacao(R.CASOS["R01"])), ensure_ascii=False)
    for proibido in ("2030", "mediana", "desvio", '"z"', '"noite"'):
        assert proibido not in texto
