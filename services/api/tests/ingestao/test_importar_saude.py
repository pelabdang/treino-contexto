"""Gravacao de limiar e zonas de FC no banco (Meta 6, #140), com as fixtures sinteticas da #135.

Esperado escrito a mao a partir da linha do tempo de tests/fixtures/garmin/gerar_fixtures_saude.py (ver tambem
test_saude_garmin.py). Retrato das zonas: dia da importacao informado nos testes (21/03/2025).
"""

import socket
from datetime import date
from pathlib import Path

import pytest
from app.db.models import Atleta, LimiarAtleta, ZonaFcAtleta
from app.ingestao.saude import importar_saude, limiar_vigente, zonas_vigentes
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

RAIZ = Path(__file__).resolve().parents[4]
PASTA = RAIZ / "tests" / "fixtures" / "garmin" / "saude"
ZIP_SAUDE = PASTA / "exportacao_saude.zip"
ZIP_SEM = PASTA / "exportacao_sem_saude.zip"
D = date
HOJE = D(2025, 3, 21)


def _linhas(session, modelo):
    return session.scalar(select(func.count()).select_from(modelo))


def _tabela(session):
    lim = [(r.grandeza, r.vigente_desde, r.valor, r.origem, r.versao_leitura)
           for r in session.scalars(select(LimiarAtleta).order_by(LimiarAtleta.id))]
    zon = [(r.esporte, r.origem, r.vigente_desde, r.metodo, r.zona1_min_bpm, r.zona5_max_bpm)
           for r in session.scalars(select(ZonaFcAtleta).order_by(ZonaFcAtleta.id))]
    return lim, zon


def test_grava_limiar_e_zonas_das_fixtures(session):
    rel = importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    assert (rel.limiar.inseridas, rel.limiar.atualizadas, rel.limiar.ignoradas) == (5, 0, 0)
    assert (rel.zonas.inseridas, rel.zonas.atualizadas, rel.zonas.ignoradas) == (6, 0, 0)
    assert _linhas(session, Atleta) == 1
    lim, zon = _tabela(session)
    assert {(g, d, round(v, 2)) for g, d, v, *_ in lim} == {
        ("fc_bpm", D(2025, 3, 5), 158.0), ("fc_bpm", D(2025, 3, 8), 159.0), ("fc_bpm", D(2025, 3, 10), 163.0),
        ("velocidade_ms", D(2025, 3, 5), 3.70), ("velocidade_ms", D(2025, 3, 10), 3.85)}
    assert {(o, ver) for *_, o, ver in lim} == {("garmin_export", "saude_garmin@1")}
    assert {(e, o, v) for e, o, v, *_ in zon} == {
        ("padrao", "garmin_export", HOJE), ("corrida", "garmin_export", HOJE), ("ciclismo", "garmin_export", HOJE),
        ("corrida", "garmin_fit", D(2025, 3, 4)), ("padrao", "garmin_fit", D(2025, 3, 7)),
        ("corrida", "garmin_fit", D(2025, 3, 11)),
    }


def test_importar_duas_vezes_da_as_mesmas_linhas(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    antes = _tabela(session)
    ids = (set(session.scalars(select(LimiarAtleta.id))), set(session.scalars(select(ZonaFcAtleta.id))))
    rel = importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    assert (rel.limiar.inseridas, rel.limiar.atualizadas, rel.limiar.ignoradas) == (0, 0, 5)
    assert (rel.zonas.inseridas, rel.zonas.atualizadas, rel.zonas.ignoradas) == (0, 0, 6)
    assert _tabela(session) == antes
    assert (set(session.scalars(select(LimiarAtleta.id))), set(session.scalars(select(ZonaFcAtleta.id)))) == ids
    assert _linhas(session, Atleta) == 1


def test_reimportar_em_outro_dia_nao_duplica_o_mesmo_retrato(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    rel = importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=D(2025, 4, 2))
    assert rel.zonas.inseridas == 0 and rel.zonas.ignoradas == 6
    assert _linhas(session, ZonaFcAtleta) == 6


def test_retrato_diferente_abre_nova_vigencia_sem_apagar_o_historico(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    antiga = session.scalars(select(ZonaFcAtleta).where(
        ZonaFcAtleta.esporte == "corrida", ZonaFcAtleta.origem == "garmin_export")).one()
    antiga.fc_max_bpm = 190  # o banco guarda um retrato anterior diferente do que o arquivo traz
    session.commit()
    rel = importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=D(2025, 5, 1))
    assert rel.zonas.inseridas == 1 and rel.zonas.ignoradas == 5
    linhas = session.scalars(select(ZonaFcAtleta).where(
        ZonaFcAtleta.esporte == "corrida", ZonaFcAtleta.origem == "garmin_export")
        .order_by(ZonaFcAtleta.vigente_desde)).all()
    assert [(z.vigente_desde, z.fc_max_bpm) for z in linhas] == [(HOJE, 190), (D(2025, 5, 1), 188)]


def test_correcao_da_fonte_na_mesma_chave_atualiza_com_aviso(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    r = session.scalars(select(LimiarAtleta).where(
        LimiarAtleta.grandeza == "fc_bpm", LimiarAtleta.vigente_desde == D(2025, 3, 8))).one()
    r.valor = 150
    session.commit()
    rel = importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    assert (rel.limiar.atualizadas, rel.limiar.ignoradas) == (1, 4)
    assert any("corrigido pela fonte" in a for a in rel.avisos)
    assert not any("150" in a or "159" in a for a in rel.avisos)  # aviso sem valor fisiologico
    assert _linhas(session, LimiarAtleta) == 5
    assert session.get(LimiarAtleta, r.id).valor == 159


def test_limiar_vigente_em_qualquer_data(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    a = session.scalars(select(Atleta)).one().id

    def fc(d):
        r = limiar_vigente(session, a, "fc_bpm", d)
        return r and r.valor

    def vel(d):
        r = limiar_vigente(session, a, "velocidade_ms", d)
        return r and r.valor

    assert fc(D(2025, 3, 4)) is None and vel(D(2025, 3, 4)) is None  # antes do primeiro: nenhum
    assert fc(D(2020, 1, 1)) is None
    assert fc(D(2025, 3, 5)) == 158 and vel(D(2025, 3, 5)) == pytest.approx(3.70)  # no proprio dia ja vale
    assert fc(D(2025, 3, 7)) == 158
    assert fc(D(2025, 3, 8)) == 159 and vel(D(2025, 3, 8)) == pytest.approx(3.70)  # so a FC mudou
    assert fc(D(2025, 3, 9)) == 159
    assert fc(D(2025, 3, 10)) == 163 and vel(D(2025, 3, 10)) == pytest.approx(3.85)
    assert fc(D(2030, 1, 1)) == 163  # sem prazo de validade


def test_limiar_informado_vence_o_da_garmin_no_mesmo_dia(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    a = session.scalars(select(Atleta)).one().id
    session.add(LimiarAtleta(atleta_id=a, grandeza="fc_bpm", valor=170, vigente_desde=D(2025, 3, 10),
                             origem="informado", versao_leitura="manual"))
    session.commit()
    assert limiar_vigente(session, a, "fc_bpm", D(2025, 3, 10)).valor == 170
    assert limiar_vigente(session, a, "fc_bpm", D(2025, 3, 9)).valor == 159


def test_zonas_vigentes_numa_data(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    a = session.scalars(select(Atleta)).one().id

    def pisos(z):
        return (z.fc_max_bpm, z.zona1_min_bpm, z.zona2_min_bpm, z.zona3_min_bpm, z.zona4_min_bpm, z.zona5_min_bpm,
                z.zona5_max_bpm)

    assert zonas_vigentes(session, a, "corrida", D(2025, 3, 3)) is None  # antes da primeira
    assert pisos(zonas_vigentes(session, a, "corrida", D(2025, 3, 4))) == (190, 95, 114, 133, 152, 171, 190)
    assert pisos(zonas_vigentes(session, a, "corrida", D(2025, 3, 10))) == (190, 95, 114, 133, 152, 171, 190)
    assert pisos(zonas_vigentes(session, a, "corrida", D(2025, 3, 11))) == (188, 94, 113, 132, 150, 169, 188)
    assert zonas_vigentes(session, a, "padrao", D(2025, 3, 6), origem="garmin_fit") is None
    assert zonas_vigentes(session, a, "padrao", D(2025, 3, 7), origem="garmin_fit").metodo == "percent_max_hr"
    retrato = zonas_vigentes(session, a, "ciclismo", HOJE, origem="garmin_export")
    assert (retrato.metodo, pisos(retrato)[0]) == ("HR_MAX", 184)
    assert zonas_vigentes(session, a, "ciclismo", D(2025, 3, 20)) is None  # o retrato so vale a partir do dia dele


def test_atleta_sem_dados_de_saude_nao_grava_nada_nem_cria_atleta(session):
    rel = importar_saude(session, ZIP_SEM, "Ana", dia_retrato=HOJE)
    assert not rel.gravou_algo and rel.avisos
    assert _linhas(session, Atleta) == _linhas(session, LimiarAtleta) == _linhas(session, ZonaFcAtleta) == 0


def test_exportacao_mais_curta_nao_apaga_o_historico(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    antes = _tabela(session)
    importar_saude(session, ZIP_SEM, "Ana", dia_retrato=HOJE)
    assert _tabela(session) == antes


def test_dois_atletas_nao_se_misturam(session):
    importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE)
    importar_saude(session, ZIP_SAUDE, "Beto", dia_retrato=HOJE)
    assert _linhas(session, LimiarAtleta) == 10 and _linhas(session, ZonaFcAtleta) == 12


def test_caminho_inexistente_levanta_filenotfound(session, tmp_path):
    with pytest.raises(FileNotFoundError):
        importar_saude(session, tmp_path / "nao_existe.zip", "Ana")


def test_sem_rede(session, monkeypatch):
    def bloqueia(*a, **k):
        raise AssertionError("importar_saude abriu conexao de rede")

    for nome in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, nome, bloqueia)
    monkeypatch.setattr(socket, "create_connection", bloqueia)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueia)
    assert importar_saude(session, ZIP_SAUDE, "Ana", dia_retrato=HOJE).gravou_algo


@pytest.mark.parametrize("campos", [
    dict(grandeza="outra", valor=1, origem="garmin_export"),
    dict(grandeza="fc_bpm", valor=0, origem="garmin_export"),
    dict(grandeza="fc_bpm", valor=1, origem="strava"),
])
def test_check_do_limiar(session, campos):
    session.add(Atleta(nome="Ana"))
    session.flush()
    session.add(LimiarAtleta(atleta_id=1, vigente_desde=D(2025, 1, 1), versao_leitura="x", **campos))
    with pytest.raises(IntegrityError):
        session.flush()


def test_unicidade_do_limiar(session):
    session.add(Atleta(nome="Ana"))
    session.flush()
    base = dict(atleta_id=1, vigente_desde=D(2025, 1, 1), versao_leitura="x")
    session.add_all([LimiarAtleta(grandeza="fc_bpm", valor=1, origem="garmin_export", **base),
                     LimiarAtleta(grandeza="fc_bpm", valor=2, origem="garmin_export", **base)])
    with pytest.raises(IntegrityError):
        session.flush()
