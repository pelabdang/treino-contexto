"""Confere as fixtures sintéticas da Meta 8 e o oráculo à mão (issue #294, ADR 0012).

NÃO roda código de produção do check-in nem da `carga_pse@1` (#296 a #298): confere que as fixtures são a saída do gerador, que
cobrem os casos da ADR e que o oráculo escrito à mão é coerente com uma referência curta e independente das regras
(`_carga_pse`, `_pendentes`, `_valida`).
"""

import importlib.util
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from app.servicos.fuso import data_local

PASTA = Path(__file__).parent / "fixtures" / "meta8"


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(f"meta8_{nome}", PASTA / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gerador = _carregar("gerar_fixtures_meta8")
oraculo = _carregar("oraculo")
P = oraculo.PARAMETROS

DADOS = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))
ATIVIDADES = DADOS["atividades"]
CHECKINS = json.loads((PASTA / "checkins.json").read_text(encoding="utf-8"))
POR_ID = {a["id"]: a for a in ATIVIDADES}
IGNORADAS = ("multiesporte_pai", "troca")
ATALHOS = {"dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse"}


def _dia(a) -> date:
    return data_local(datetime.fromisoformat(a["inicio"]), a["fuso_min"])


def _elegivel(a) -> bool:
    return a["subtipo"] not in IGNORADAS


def _carga_pse(a):
    """Referência da carga_pse@1 (ADR 0012, item 6): PSE x duracao_s / 60, só para atividade elegível."""
    if not _elegivel(a):
        return None
    minutos = a["duracao_s"] / 60
    c = CHECKINS.get(a["id"])
    if c is None:
        return ("sem_checkin", minutos, None)
    if a["duracao_s"] <= 0:
        return ("sem_duracao", minutos, None)
    return ("calculada", minutos, c["pse"] * minutos)


def _pendentes(agora: str, dias: int):
    hoje = datetime.fromisoformat(agora).date()
    pend = [a for a in ATIVIDADES if _elegivel(a) and a["id"] not in CHECKINS and _dia(a) >= hoje - timedelta(days=dias)]
    return [a["id"] for a in sorted(pend, key=lambda a: a["inicio"], reverse=True)]


def _valida(corpo: dict):
    """Referência das regras do corpo do PUT (ADR 0012, itens 1 e 2). Devolve (válido, motivo)."""
    for campo in ("pse", "sensacao", "nada_a_relatar"):
        if campo not in corpo:
            return False, "obrigatorio"
    if not 0 <= corpo["pse"] <= 10:
        return False, "pse"
    if not 1 <= corpo["sensacao"] <= 5:
        return False, "sensacao"
    atalhos = corpo.get("atalhos", [])
    if len(set(atalhos)) != len(atalhos) or not set(atalhos) <= ATALHOS:
        return False, "atalho"
    texto = corpo.get("texto")
    if texto is not None and len(texto) > P["TEXTO_MAX"]:
        return False, "texto"
    texto = texto.strip() if texto else None
    texto = texto or None
    if corpo["nada_a_relatar"]:
        return (not atalhos and texto is None), "observacao"
    return (bool(atalhos) or texto is not None), "observacao"


# ---- fixtures ------------------------------------------------------------------------------------------------------

def test_json_versionado_e_a_saida_do_gerador():
    assert json.loads(json.dumps(gerador.gerar())) == DADOS
    assert json.loads(json.dumps(gerador.CHECKINS)) == CHECKINS


def test_ids_unicos_e_check_ins_apontam_para_atividades_elegiveis():
    assert len({a["id"] for a in ATIVIDADES}) == len(ATIVIDADES)
    assert set(CHECKINS) <= {a["id"] for a in ATIVIDADES if _elegivel(a)}
    assert DADOS["agora"] == P["AGORA"]
    for a in ATIVIDADES:
        assert a["id"].startswith(_dia(a).isoformat())


def test_casos_da_adr_estao_nas_fixtures():
    assert {a["modalidade"] for a in ATIVIDADES} == {"corrida", "natacao", "ciclismo", "outra"}
    assert {a["subtipo"] for a in ATIVIDADES} >= {"multiesporte_pai", "troca", None, "virtual", "piscina", "aguas_abertas"}
    assert POR_ID["2026-11-01/cor2"]["inicio"].startswith("2026-11-02")  # UTC já é 02/11, local é 01/11
    assert POR_ID["2026-11-02/cor1"]["fuso_min"] is None
    assert POR_ID["2026-11-04/cic1"]["subtipo"] is None and "2026-11-04/cic1" not in CHECKINS  # subtipo nulo pendente
    assert POR_ID["2026-11-09/cor1"]["duracao_s"] == 0
    assert any(c["pse"] == 0 for c in CHECKINS.values())
    assert any(c["nada_a_relatar"] for c in CHECKINS.values())
    assert any(not c["nada_a_relatar"] and not c["atalhos"] and c["texto"] for c in CHECKINS.values())  # só texto
    assert "2026-10-15/cor1" in CHECKINS and _dia(POR_ID["2026-10-15/cor1"]) < date(2026, 11, 2)  # editável fora do prazo


def test_todo_check_in_das_fixtures_e_valido():
    for id_, c in CHECKINS.items():
        assert _valida(c)[0], id_


# ---- oráculo -------------------------------------------------------------------------------------------------------

def test_oraculo_cobre_toda_atividade():
    assert set(oraculo.CARGA_PSE_ESPERADA) == set(POR_ID)
    assert {i for i, v in oraculo.CARGA_PSE_ESPERADA.items() if v is None} == oraculo.NAO_ELEGIVEIS


@pytest.mark.parametrize("id_", sorted(oraculo.CARGA_PSE_ESPERADA))
def test_carga_pse_do_oraculo_bate_com_a_referencia(id_):
    esperado, ref = oraculo.CARGA_PSE_ESPERADA[id_], _carga_pse(POR_ID[id_])
    if esperado is None:
        assert ref is None
        return
    assert esperado[0] == ref[0]
    assert esperado[1] == pytest.approx(ref[1])
    if esperado[2] is None:
        assert ref[2] is None
    else:
        assert esperado[2] == pytest.approx(ref[2])


def test_carga_pse_a_mao():
    # PSE x minutos, escrito aqui sem ler as fixtures
    assert 6 * (2700 / 60) == 270.0
    assert 4 * (2400 / 60) == 160.0
    assert 7 * (3000 / 60) == 350.0
    assert 6 * (2725 / 60) == pytest.approx(272.5)
    assert 0 * (1800 / 60) == 0.0


@pytest.mark.parametrize("chave", sorted(oraculo.PENDENTES))
def test_pendentes_do_oraculo(chave):
    agora, dias = chave
    assert _pendentes(agora, dias) == oraculo.PENDENTES[chave]


def test_prazo_de_criar_usa_a_data_local():
    hoje = date.fromisoformat(P["HOJE"])
    for id_, esperado in oraculo.PRAZO_CRIAR.items():
        a = POR_ID[id_]
        if esperado is None:
            assert not _elegivel(a)
        else:
            assert (_dia(a) >= hoje - timedelta(days=P["PRAZO_DIAS"])) is esperado, id_


@pytest.mark.parametrize("descricao,corpo,valido,motivo", oraculo.VALIDACAO, ids=[v[0] for v in oraculo.VALIDACAO])
def test_validacao_do_corpo(descricao, corpo, valido, motivo):
    ok, m = _valida(corpo)
    assert ok is valido
    if not valido:
        assert m == motivo
