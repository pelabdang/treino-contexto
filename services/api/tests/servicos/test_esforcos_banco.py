"""Blocos e esforços no banco (issue #166; ADR 0008, item 9), com as fixtures sintéticas da #161."""

import importlib.util
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, BlocoAtividade, Segmento
from app.ingestao.garmin import ler_atividade_fit
from app.ingestao.importacao import duracao_da, gravar_atividade
from app.metricas import esforcos as ef
from app.servicos.esforcos import PedaladaHistorico, detectar_esforcos, velocidade_habitual
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

RAIZ = Path(__file__).parents[4]
PASTA_FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"
ORACULO = Path(__file__).parents[1] / "metricas" / "test_esforcos_oraculo.py"


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def session():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        yield s
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


def _historico(session, atleta, modalidade, ref):
    """Uma atividade longa antes da fixture (sem voltas), com o ritmo (s/km) ou a velocidade (km/h) de referência."""
    if modalidade == "corrida":
        dist, dur = 5000.0, 5000.0 * ref / 1000
    else:
        dur = 3600.0
        dist = ref * dur / 3.6
    session.add(Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id=f"hist-{modalidade}", modalidade=modalidade,
        inicio=datetime(2020, 1, 1, 8, tzinfo=timezone.utc), duracao_s=dur, distancia_m=dist,
    ))
    session.commit()


def _fit(session, atleta, nome):
    a = ler_atividade_fit((PASTA_FIT / nome).read_bytes(), fonte="fit_upload")
    _, ativ, _ = gravar_atividade(session, atleta.id, a, duracao_da(a), [])
    session.commit()
    return ativ


def _carregar(session, atleta, oraculo, nome):
    modalidade, ref, _ = oraculo.ESPERADO[nome]
    _historico(session, atleta, modalidade, ref)
    return _fit(session, atleta, nome)


def _blocos(session, ativ):
    return session.scalars(
        select(BlocoAtividade).where(BlocoAtividade.atividade_id == ativ.id).order_by(BlocoAtividade.ordem)
    ).all()


def test_ha_um_oraculo_para_cada_fit(oraculo):
    assert {p.name for p in PASTA_FIT.iterdir()} == set(oraculo.ESPERADO)


@pytest.mark.parametrize("nome", [
    "esforcos_corrida_400_com_pausa.fit", "esforcos_corrida_1500_lap_automatico.fit",
    "esforcos_corrida_continuo_forte.fit", "esforcos_corrida_rodagem_leve.fit", "esforcos_corrida_misto.fit",
    "esforcos_ciclismo_blocos_4min.fit", "esforcos_ciclismo_lap_automatico.fit",
])
def test_blocos_no_banco_batem_com_o_oraculo(session, atleta, oraculo, nome):
    modalidade, _ref, esperado = oraculo.ESPERADO[nome]
    ativ = _carregar(session, atleta, oraculo, nome)
    rel = detectar_esforcos(session, atleta.id)
    assert rel.versao == ef.VERSAO and rel.alteradas == 1  # só a atividade da fixture tem voltas
    blocos = _blocos(session, ativ)
    assert len(blocos) == len(esperado)
    for b, e in zip(blocos, esperado):
        assert (b.categoria, b.volta_inicial, b.volta_final) == (e.categoria, e.volta_inicial, e.volta_final)
        assert b.distancia_m == pytest.approx(e.distancia_m, abs=0.01)
        assert b.duracao_s == pytest.approx(e.duracao_s, abs=1e-3)
        assert b.fc_media == pytest.approx(e.fc_media, abs=1e-3)
        assert b.parada_apos_s == pytest.approx(e.parada_apos_s, abs=1e-3)
        assert b.faixa == e.faixa
        assert b.treino_chave == e.treino_chave
        assert b.versao_deteccao == ef.VERSAO
        intensidade = b.pace_s_km if modalidade == "corrida" else b.distancia_m / b.duracao_s * 3.6
        assert intensidade == pytest.approx(e.intensidade, abs=0.01)
    n_voltas = session.scalar(select(func.count()).select_from(Segmento).where(Segmento.atividade_id == ativ.id))
    assert blocos[-1].volta_final + 1 == n_voltas  # os blocos cobrem todas as voltas


def test_segunda_rodada_nao_muda_nada(session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_misto.fit")
    detectar_esforcos(session, atleta.id)
    antes = [(b.id, b.ordem, b.categoria, b.faixa, b.versao_deteccao) for b in _blocos(session, ativ)]
    rel = detectar_esforcos(session, atleta.id)
    assert (rel.alteradas, rel.inalteradas) == (0, 2)  # a atividade da fixture e o histórico (sem voltas)
    assert [(b.id, b.ordem, b.categoria, b.faixa, b.versao_deteccao) for b in _blocos(session, ativ)] == antes
    assert session.scalar(select(func.count()).select_from(BlocoAtividade)) == 27


def test_versao_nova_redetecta_tudo(session, atleta, oraculo, monkeypatch):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_1500_lap_automatico.fit")
    detectar_esforcos(session, atleta.id)
    monkeypatch.setattr(ef, "VERSAO", "esforcos@2")
    rel = detectar_esforcos(session, atleta.id)
    assert rel.versao == "esforcos@2" and rel.alteradas == 1
    novos = _blocos(session, ativ)
    assert len(novos) == 5 and {b.versao_deteccao for b in novos} == {"esforcos@2"}
    assert detectar_esforcos(session, atleta.id).alteradas == 0


def test_voltas_que_mudam_refazem_os_blocos(session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_rodagem_leve.fit")
    detectar_esforcos(session, atleta.id)
    assert [b.categoria for b in _blocos(session, ativ)] == ["leve"]
    for s in ativ.segmentos:  # as voltas foram corrigidas: agora são rápidas
        s.duracao_s = s.duracao_s * 0.6
    session.commit()
    rel = detectar_esforcos(session, atleta.id)
    assert rel.alteradas == 1 and {b.categoria for b in _blocos(session, ativ)} == {"esforco"}


def test_relatorio(session, atleta, oraculo):
    _carregar(session, atleta, oraculo, "esforcos_corrida_continuo_forte.fit")
    rel = detectar_esforcos(session, atleta.id)
    assert rel.processadas == 2 and rel.esforcos["corrida"] == 1 and rel.treinos_chave["corrida"] == 1
    assert rel.sem_blocos == 1  # o histórico não tem voltas
    assert rel.referencia_da_atividade == 0
    assert rel.esforcos["ciclismo"] == 0


def test_sem_historico_usa_a_referencia_da_atividade(session, atleta):
    _fit(session, atleta, "esforcos_corrida_rodagem_leve.fit")
    rel = detectar_esforcos(session, atleta.id)
    assert rel.referencia_da_atividade == 1


def test_so_corrida_e_ciclismo_e_so_do_atleta(session, atleta, oraculo):
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    _carregar(session, outro, oraculo, "esforcos_corrida_misto.fit")
    ativ = _fit(session, atleta, "esforcos_ciclismo_lap_automatico.fit")
    ativ.modalidade = "natacao"
    session.commit()
    rel = detectar_esforcos(session, atleta.id)
    assert rel.processadas == 0
    assert session.scalar(select(func.count()).select_from(BlocoAtividade)) == 0


def test_atividade_ids_limita_a_rodada(session, atleta, oraculo):
    a = _carregar(session, atleta, oraculo, "esforcos_corrida_misto.fit")
    assert detectar_esforcos(session, atleta.id, atividade_ids=[a.id + 100]).processadas == 0
    rel = detectar_esforcos(session, atleta.id, atividade_ids=[a.id])
    assert rel.processadas == 1 and rel.alteradas == 1


def test_apagar_a_atividade_apaga_os_blocos(session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_misto.fit")
    detectar_esforcos(session, atleta.id)
    session.delete(ativ)
    session.commit()
    assert session.scalar(select(func.count()).select_from(BlocoAtividade)) == 0


def test_check_de_categoria_e_unicidade(session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_rodagem_leve.fit")
    base = dict(atividade_id=ativ.id, volta_inicial=0, volta_final=0, inicio_offset_s=0, duracao_s=1,
                versao_deteccao="esforcos@1")
    session.add(BlocoAtividade(ordem=0, categoria="tiro", **base))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add_all([BlocoAtividade(ordem=0, categoria="leve", **base), BlocoAtividade(ordem=0, categoria="leve", **base)])
    with pytest.raises(IntegrityError):
        session.commit()


def test_velocidade_habitual():
    hoje = date(2025, 6, 1)

    def p(dias, kmh, horas=1.0, indoor=False):
        return PedaladaHistorico(hoje - timedelta(days=dias), kmh * horas * 1000, horas * 3600, indoor)

    assert velocidade_habitual([], hoje) is None
    # só pedaladas de mais de 30 min, fora do trainer e antes da sessão
    historico = [p(5, 20), p(6, 24), p(7, 22), p(8, 30, horas=0.5), p(9, 40, indoor=True), p(0, 50)]
    assert velocidade_habitual(historico, hoje) == pytest.approx(22.0)  # mediana de 20, 22, 24
    # com 10 na janela, a mediana é só da janela; as antigas ficam de fora
    janela = [p(d, 25) for d in range(1, 11)]
    assert velocidade_habitual(janela + [p(200, 10)] * 3, hoje) == pytest.approx(25.0)
    # com menos de 10 na janela, todo o histórico anterior
    assert velocidade_habitual([p(1, 30), p(200, 10), p(201, 10)], hoje) == pytest.approx(10.0)
