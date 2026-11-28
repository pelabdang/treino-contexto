"""`checagens_chat@1` (issue #595, ADR 0017, item 4) contra as fixtures sintéticas da #592: toda resposta boa passa e toda ruim reprova
exatamente pelos motivos declarados. Regras próprias do projeto, sem artigo (ver `docs/metricas/checagens-chat.md`)."""

import json
from pathlib import Path

import pytest
from app.explicacao import checagens_chat as ck

PASTA = Path(__file__).parents[1] / "fixtures" / "chat"
DADOS = json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))
CASOS = DADOS["casos"]


def _ids():
    return [c["id"] for c in CASOS]


@pytest.mark.parametrize("caso", [c for c in CASOS if c["categoria"] not in ("fora_do_tema", "pedido_de_mudanca")], ids=lambda c: c["id"])
def test_resposta_boa_passa(caso):
    r = ck.checar_texto(caso["ferramentas_esperadas"], caso["resposta_boa"])
    assert r.aprovado, r.motivos


@pytest.mark.parametrize("caso", CASOS, ids=_ids())
def test_resposta_ruim_reprova_pelos_motivos_declarados(caso):
    r = ck.checar_texto(caso["ferramentas_esperadas"], caso["resposta_ruim"]["texto"])
    assert not r.aprovado
    assert set(r.motivos) == set(caso["resposta_ruim"]["motivos_esperados"]), r.motivos


@pytest.mark.parametrize("caso", [c for c in CASOS if c["categoria"] in ("fora_do_tema", "pedido_de_mudanca")], ids=lambda c: c["id"])
def test_recusa_e_o_texto_fixo_do_codigo(caso):
    (f,) = caso["ferramentas_esperadas"]
    assert ck.texto_da_recusa(f["argumentos"]["motivo"]) == caso["resposta_boa"]
    assert not ck.checar_texto(caso["ferramentas_esperadas"], caso["resposta_boa"]).aprovado  # o modelo escrevendo o mesmo texto não passa


def test_resultado_nunca_repete_o_texto():
    r = ck.checar_texto([], "Você correu 99 km por causa do calor.")
    assert all(m in ck.MOTIVOS for m in r.motivos)
    assert "99" not in repr(r) and "calor" not in repr(r)


def test_versao_e_motivos_batem_com_a_adr():
    assert ck.VERSAO == "checagens_chat@1"
    assert len(set(ck.MOTIVOS)) == len(ck.MOTIVOS)
