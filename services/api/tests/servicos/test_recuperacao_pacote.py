"""Adaptador da recuperacao no pacote (issue #374, ADR 0014 itens 2 e 4): as noites gravadas viram o bloco `recuperacao` do
`fatos_treino@2` e o `importado_em` da noite do treino. Oraculo a mao: `tests/fixtures/meta10/oraculo_fatos_recuperacao.py`.
Tudo sintetico; nada de banco real."""

import importlib.util
import json
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino
from app.explicacao.fatos_treino import VERSAO
from app.servicos.feedback import desatualizado
from app.servicos.feedback_fatos import fatos_da_atividade
from app.servicos.recuperacao_banco import gravar_noite, noites_do_atleta
from app.servicos.recuperacao_pacote import (
    carregar_da_atividade,
    carregar_do_atleta,
    importado_em_de_hoje,
    mesmo_instante,
)

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta10"
_spec = importlib.util.spec_from_file_location("oraculo_meta10_adaptador", PASTA / "oraculo_fatos_recuperacao.py")
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)

GRAVADO = datetime(2030, 3, 15, 9, 0, tzinfo=UTC)
MARCADOR = "MARCADOR-TEXTO-LIVRE-374"


def _semear(session, caso, hora=None):
    """Atleta, as noites do caso do oraculo, uma corrida em `dia`/`hora` do caso (fuso 0) e o check-in com texto livre."""
    c = R.CASOS[caso]
    atleta = Atleta(nome="Atleta Ficticio")
    session.add(atleta)
    session.flush()
    for n in c["noites"]:
        gravar_noite(session, atleta.id, n["noite"], n["sono_s"], n["vfc_ms"], n["fc_repouso_bpm"], "teste", GRAVADO)
    h = hora or c["hora"]
    ativ = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=caso, modalidade="corrida", subtipo="esteira", tipo_treino="longo",
                     inicio=datetime.combine(c["dia"], h, tzinfo=UTC), fuso_min=0, duracao_s=3000.0, distancia_m=8000.0)
    session.add(ativ)
    session.flush()
    checkin = CheckinTreino(atividade_id=ativ.id, pse=5, sensacao=3, nada_a_relatar=False, texto=MARCADOR, versao="checkin@1",
                            registrado_em=GRAVADO, atualizado_em=GRAVADO)
    session.add(checkin)
    session.commit()
    return ativ, checkin


@pytest.mark.parametrize("caso", list(R.CASOS))
def test_o_bloco_do_banco_e_igual_ao_do_oraculo(session, caso):
    ativ, checkin = _semear(session, caso)
    pacote = fatos_da_atividade(session, ativ, checkin)
    assert pacote["versao"] == VERSAO and pacote["recuperacao"] == R.CASOS[caso]["bloco"]


def test_a_leitura_por_atividade_e_a_do_lote_dao_o_mesmo_bloco(session):
    ativ, checkin = _semear(session, "R01")
    lote = carregar_do_atleta(session, ativ.atleta_id)
    assert fatos_da_atividade(session, ativ, checkin, lote) == fatos_da_atividade(session, ativ, checkin)


def test_fora_do_periodo_usa_a_primeira_noite_do_atleta_e_nao_a_da_janela(session):
    # R06: o treino e 20 dias antes de DIA; a janela D-28..D traz noites, mas a primeira do atleta (D-14) e posterior ao treino.
    ativ, _ = _semear(session, "R06")
    dados = carregar_da_atividade(session, ativ)
    assert dados.primeira == R.DIA - timedelta(days=14)
    assert importado_em_de_hoje(dados, ativ) is None


def test_o_pacote_nao_leva_serie_data_identificador_nem_texto_livre(session):
    ativ, checkin = _semear(session, "R01")
    texto = json.dumps(fatos_da_atividade(session, ativ, checkin), ensure_ascii=False)
    noites = noites_do_atleta(session, ativ.atleta_id)
    for noite, g in noites.items():
        assert noite.isoformat() not in texto and str(noite.day) + "/" not in texto
        assert g.importado_em.isoformat() not in texto
    assert MARCADOR not in texto
    bloco = json.loads(texto)["recuperacao"]
    so_bloco = json.dumps(bloco, ensure_ascii=False)
    for proibida in ("importado", "atleta", "mediana", "desvio", "\"z\"", "mad", "origem", "garmin", "26100"):  # 26100 s = 435 min, o normal em segundos
        assert proibida not in so_bloco, proibida
    assert set(bloco) == set(R.CHAVES_BLOCO_OK)
    assert all(set(m) == set(R.CHAVES_MEDIDA) for m in bloco["medidas"])


def test_atividade_sem_recuperacao_gera_o_pacote(session):
    ativ, checkin = _semear(session, "R04")
    from app.db.models import RecuperacaoDia

    session.query(RecuperacaoDia).delete()
    session.commit()
    pacote = fatos_da_atividade(session, ativ, checkin)
    assert pacote["recuperacao"] == {"versao": "recuperacao@1", "estado": "sem_dado", "motivo": "sem_noite"}
    assert pacote["checkin"]["pse"] == 5


# ---------- "desatualizado" (ADR 0014, item 4b) ----------

def _feedback(session, checkin, em):
    fb = FeedbackTreino(checkin_id=checkin.id, estado="pronto", texto="x", versao_fatos=VERSAO, versao_prompt="p", versao_checagens="c", provedor="falso", modelo="falso",
                        checkin_atualizado_em=checkin.atualizado_em, recuperacao_importada_em=em, tentado_em=GRAVADO)
    session.add(fb)
    session.commit()
    return fb


def test_noite_que_chega_depois_desatualiza(session):
    ativ, checkin = _semear(session, "R04")  # a noite do treino nao existe
    fb = _feedback(session, checkin, None)
    hoje = importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ)
    assert hoje is None and not desatualizado(fb, checkin, VERSAO, hoje)
    gravar_noite(session, ativ.atleta_id, R.DIA, 25000, None, None, "teste", GRAVADO + timedelta(hours=1))
    session.commit()
    hoje = importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ)
    assert mesmo_instante(hoje, GRAVADO + timedelta(hours=1)) and desatualizado(fb, checkin, VERSAO, hoje)


def test_valor_que_muda_desatualiza_e_igual_nao(session):
    ativ, checkin = _semear(session, "R01")
    fb = _feedback(session, checkin, GRAVADO)
    dados = carregar_do_atleta(session, ativ.atleta_id)
    assert not desatualizado(fb, checkin, VERSAO, importado_em_de_hoje(dados, ativ))
    gravar_noite(session, ativ.atleta_id, R.DIA, 345 * 60, 41, 58, "teste", GRAVADO + timedelta(hours=2))  # tres valores iguais
    assert not desatualizado(fb, checkin, VERSAO, importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ))
    gravar_noite(session, ativ.atleta_id, R.DIA, 350 * 60, 41, 58, "teste", GRAVADO + timedelta(hours=2))  # sono mudou
    assert desatualizado(fb, checkin, VERSAO, importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ))


def test_treino_de_madrugada_com_noite_gravada_nunca_desatualiza_por_isso(session):
    ativ, checkin = _semear(session, "R05")  # 05:59, noite gravada
    fb = _feedback(session, checkin, None)
    hoje = importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ)
    assert hoje is None and not desatualizado(fb, checkin, VERSAO, hoje)


def test_fora_do_periodo_vale_none_dos_dois_lados(session):
    ativ, checkin = _semear(session, "R06")
    fb = _feedback(session, checkin, None)
    assert not desatualizado(fb, checkin, VERSAO, importado_em_de_hoje(carregar_do_atleta(session, ativ.atleta_id), ativ))


def test_sem_o_argumento_a_recuperacao_nao_entra_na_conta(session):
    ativ, checkin = _semear(session, "R01")
    fb = _feedback(session, checkin, None)  # gravado sem noite, mas a noite existe
    assert not desatualizado(fb, checkin, VERSAO)


def test_mesmo_instante_normaliza_o_fuso_dos_dois_lados():
    com_fuso = datetime(2030, 3, 15, 9, 0, tzinfo=UTC)
    assert mesmo_instante(com_fuso, com_fuso.replace(tzinfo=None))  # o SQLite devolve sem fuso
    assert mesmo_instante(None, None) and not mesmo_instante(None, com_fuso) and not mesmo_instante(com_fuso, None)
    assert not mesmo_instante(com_fuso, com_fuso + timedelta(seconds=1))
