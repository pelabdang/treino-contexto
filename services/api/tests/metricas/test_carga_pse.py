"""`carga_pse@1`: PSE x minutos (issue #297, ADR 0012), contra o oráculo das fixtures da Meta 8 (#294) e bordas à mão."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from app.metricas import carga_pse as cp

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta8"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta8_cp", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ORACULO = _oraculo()
ATIVIDADES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
CHECKINS = json.loads((PASTA / "checkins.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("a", ATIVIDADES, ids=[a["id"] for a in ATIVIDADES])
def test_oraculo_das_fixtures(a):
    pse = CHECKINS[a["id"]]["pse"] if a["id"] in CHECKINS else None
    r = cp.carga_pse(pse, a["duracao_s"], a["subtipo"])
    esperado = ORACULO.CARGA_PSE_ESPERADA[a["id"]]
    if esperado is None:
        assert r is None
        return
    estado, minutos, valor = esperado
    assert r.versao == "carga_pse@1" and r.estado == estado
    assert r.minutos == pytest.approx(minutos)
    if valor is None:
        assert r.valor is None
    else:
        assert r.valor == pytest.approx(valor)


@pytest.mark.parametrize("pse,duracao_s,valor", [
    (6, 2700, 270.0), (4, 2400, 160.0), (7, 3000, 350.0), (6, 2725, 272.5), (0, 1800, 0.0), (10, 3600, 600.0), (1, 60, 1.0),
])
def test_valores_a_mao(pse, duracao_s, valor):
    r = cp.carga_pse(pse, duracao_s)
    assert (r.estado, r.pse) == ("calculada", pse) and r.valor == pytest.approx(valor)


def test_sem_checkin_nao_estima_a_pse():
    r = cp.carga_pse(None, 2700)
    assert (r.estado, r.pse, r.valor, r.minutos) == ("sem_checkin", None, None, 45.0)


def test_sem_duracao_com_checkin():
    for d in (0, -5):
        r = cp.carga_pse(5, d)
        assert (r.estado, r.valor, r.minutos) == ("sem_duracao", None, 0.0)


def test_pai_e_troca_nao_tem_carga_pela_pse():
    assert cp.carga_pse(5, 2700, "multiesporte_pai") is None
    assert cp.carga_pse(None, 120, "troca") is None
    assert cp.elegivel(None) and cp.elegivel("piscina") and not cp.elegivel("troca")


def test_natacao_e_qualquer_subtipo_tem_carga():
    assert cp.carga_pse(4, 2400, "piscina").valor == 160.0
    assert cp.carga_pse(5, 1800, "aguas_abertas").valor == 150.0


@pytest.mark.parametrize("pse", [-1, 11])
def test_pse_fora_da_faixa_levanta_sem_repetir_o_valor(pse):
    with pytest.raises(ValueError, match="^PSE fora de 0 a 10$"):
        cp.carga_pse(pse, 2700)
