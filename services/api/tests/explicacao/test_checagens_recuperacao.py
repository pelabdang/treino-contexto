"""`checagens_feedback@5` (issue #375, ADR 0014, item 6): a linguagem e as regras mecânicas da recuperação da noite.
Textos e pacotes em `tests/fixtures/meta10/textos_recuperacao.py`; tudo sintético."""

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


O9 = _carregar("meta9", "oraculo.py", "oraculo_meta9_checagens_rec")
R = _carregar("meta10", "oraculo_fatos_recuperacao.py", "oraculo_meta10_checagens_rec")
T = _carregar("meta10", "textos_recuperacao.py", "textos_meta10_checagens_rec")


def _pacote(caso):
    """O F01 da meta 9 com o bloco `recuperacao` do caso do oráculo da meta 10."""
    bloco = T.BLOCOS_EXTRA[caso] if caso in T.BLOCOS_EXTRA else R.CASOS[caso]["bloco"]
    return {**O9.PACOTES["F01"], "recuperacao": bloco}


def test_codigos_novos_e_versao():
    assert ck.VERSAO == "checagens_feedback@5"
    novos = {"linguagem_julgamento", "recuperacao_mistura", "recuperacao_forma", "recuperacao_outro_dia", "recuperacao_sem_pacote"}
    assert novos <= set(ck.MOTIVOS) and len(set(ck.MOTIVOS)) == len(ck.MOTIVOS)


@pytest.mark.parametrize("i", list(T.BONS))
def test_texto_bom_passa(i):
    caso, texto = T.BONS[i]
    assert ck.checar_texto(_pacote(caso), texto).motivos == ()


@pytest.mark.parametrize("i", list(T.RUINS))
def test_texto_ruim_reprova_com_o_motivo_certo(i):
    caso, texto, motivo = T.RUINS[i]
    assert motivo in ck.MOTIVOS
    assert motivo in ck.checar_texto(_pacote(caso), texto).motivos


def test_pacote_sem_o_bloco_nao_aceita_recuperacao_no_texto():
    pacote = {**O9.PACOTES["F01"], "recuperacao": None}
    assert ck.checar_texto(pacote, T.BONS["B01"][1]).motivos
    assert "recuperacao_sem_pacote" in ck.checar_texto(pacote, T.BONS["B01"][1]).motivos


def test_o_resultado_nao_repete_o_texto_nem_o_termo():
    caso, texto, _ = T.RUINS["M07"]
    bruto = repr(ck.checar_texto(_pacote(caso), texto))
    assert "VFC" not in bruto and "baixa" not in bruto


def test_atalho_sono_ruim_continua_so_como_rotulo_marcado():
    pacote = _pacote("R01")
    pacote["checkin"] = {**pacote["checkin"], "atalhos": ["sono_ruim"]}
    ok = "\n".join([T.L1, T.L2, "Você marcou sono ruim.", T.SONO, T.FC_VFC])
    assert ck.checar_texto(pacote, ok).motivos == ()
    mistura = "\n".join([T.L1, T.L2, "Na noite anterior você marcou sono ruim e dormiu 5 h 45 min.", T.FC_VFC])
    assert "linguagem_julgamento" in ck.checar_texto(pacote, mistura).motivos


def test_dentro_do_seu_normal_da_recuperacao_nao_repete_o_do_resultado():
    # B01 tem "dentro do seu normal" na linha das métricas e na da VFC; duas linhas da RECUPERAÇÃO com ele repetem.
    caso, texto = T.BONS["B01"]
    assert "conclusao_repetida" not in ck.checar_texto(_pacote(caso), texto).motivos
    dupla = "\n".join([T.L1, "Na noite anterior a VFC foi 41 ms, dentro do seu normal.", "A VFC foi 41 ms, dentro do seu normal.", T.CK])
    assert "conclusao_repetida" in ck.checar_texto(_pacote("R01"), dupla).motivos


def test_unidades_ms_e_composta():
    from app.explicacao.checagens import _numeros_do_texto

    assert list(_numeros_do_texto("a vfc foi 41 ms")) == [("41", "ms")]


def test_concordancia_nao_pega_o_que_esta_certo():
    pacote = _pacote("R01")
    for ok in ("A FC do melhor tiro foi 171 bpm.", "Sua FC média foi 146 bpm.", "Natação de 1.600 m em 40 min, com FC média de 128 bpm.",
               "A VFC foi 41 ms, dentro do seu normal.", "A FC de repouso foi 58 bpm.", "A FC maior foi 171 bpm.", "A FC menor foi 120 bpm.", "A FC é igual à do treino anterior.", "A FC estável e normal."):
        assert "concordancia_sigla" not in ck.checar_texto(pacote, ok + "\nLinha dois.\nLinha três.").motivos


def test_duas_frases_na_mesma_linha_da_recuperacao_passam_se_cabem_nos_140_caracteres():
    """A ADR 0014 (item 6) já traz 'Na noite anterior você dormiu 6 h 20 min. Ainda aprendendo ...' numa linha: não é defeito."""
    caso, texto = T.BONS["B03"]
    assert "Ainda aprendendo" in texto and "6 h 20 min. Ainda" in texto
    assert ck.checar_texto(_pacote(caso), texto).motivos == ()
