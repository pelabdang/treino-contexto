"""Carga por atividade no banco e worker.calcular_carga (issue #141, ADR 0010 itens 4, 5 e 7).

Ponta a ponta com as fixtures sintéticas de ``tests/fixtures/garmin/carga/``: importa as atividades e a saúde, calcula e
confere cada linha com o oráculo da #137 (``ESPERADO``, ``SEM_SAUDE``, ``TOTAIS``, ``TOTAIS_SEM_SAUDE``).
"""

import importlib.util
import os
import socket
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CargaAtividade, LimiarAtleta
from app.ingestao.importacao import importar
from app.ingestao.saude import importar_saude
from app.metricas import carga as cg
from app.servicos.carga import calcular_carga_do_atleta
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from worker import calcular_carga, importar_garmin

RAIZ = Path(__file__).resolve().parents[3]
PASTA = RAIZ / "tests" / "fixtures" / "garmin" / "carga"
ZIP = PASTA / "exportacao_carga.zip"
ZIP_SEM = PASTA / "exportacao_carga_sem_saude.zip"

# O oráculo da #137 é carregado por caminho (tests/ não é pacote).
_spec = importlib.util.spec_from_file_location(
    "_carga_oraculo_w", RAIZ / "services" / "api" / "tests" / "metricas" / "test_carga_oraculo.py")
_o = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _o
_spec.loader.exec_module(_o)
ESPERADO, SEM_SAUDE, TOTAIS, TOTAIS_SEM_SAUDE = _o.ESPERADO, _o.SEM_SAUDE, _o.TOTAIS, _o.TOTAIS_SEM_SAUDE


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def fabrica(engine, monkeypatch):
    from app.db import session as sessao
    f = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(sessao, "SessionLocal", f)
    return f


def _carrega(session, zip_=ZIP):
    importar(session, str(zip_), "Ana")
    importar_saude(session, str(zip_), "Ana")
    return session.scalars(select(Atleta)).one().id


def _linhas(session):
    """fonte_id (int) -> CargaAtividade."""
    q = select(Atividade.fonte_id, CargaAtividade).join(CargaAtividade, CargaAtividade.atividade_id == Atividade.id)
    return {int(f): c for f, c in session.execute(q)}


def _snapshot(session):
    return {f: (c.id, c.entrada, c.versao, c.calculado_em, c.carga) for f, c in _linhas(session).items()}


# ---------------------------------------------------------------------------------------------
# Oráculo
# ---------------------------------------------------------------------------------------------
def test_fixtures_dao_a_carga_do_oraculo(session):
    atleta_id = _carrega(session)
    rel = calcular_carga_do_atleta(session, atleta_id)
    linhas = _linhas(session)
    assert set(linhas) == set(ESPERADO)  # sem linha para as ignoradas
    for id_, e in ESPERADO.items():
        c = linhas[id_]
        assert (c.estado, c.motivo, c.metodo, c.granularidade) == (e.estado, e.motivo, e.metodo, e.granularidade), id_
        for campo in ("carga", "carga_rtss", "carga_hrtss", "cobertura_pct"):
            esperado = getattr(e, campo)
            if esperado is None:
                assert getattr(c, campo) is None, (id_, campo)
            else:
                assert getattr(c, campo) == pytest.approx(esperado, abs=1e-5), (id_, campo)
        assert c.versao == cg.VERSAO and len(c.entrada) == 64 and c.calculado_em is not None
        if e.estado == "calculada":
            assert c.limiar_vigente_desde is not None
            usado = c.limiar_velocidade_ms if e.metodo == "rtss" else c.limiar_fc_bpm
            assert usado is not None
        else:
            assert c.limiar_vigente_desde is None and c.limiar_fc_bpm is None and c.limiar_velocidade_ms is None
    assert rel.calculadas == TOTAIS["calculadas"]
    assert rel.sem_carga_total == TOTAIS["sem_carga_total"]
    assert rel.sem_carga == TOTAIS["por_motivo"]
    assert rel.ignoradas_multiesporte == TOTAIS["ignoradas_multiesporte"]
    assert rel.processadas + rel.ignoradas_multiesporte == TOTAIS["atividades_importadas"]
    assert rel.gravadas == rel.processadas and rel.inalteradas == 0


def test_limiar_vigente_desde_e_o_do_metodo_vencedor(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    linhas = _linhas(session)
    # 4000000003 (05/03): rtss com limiar de velocidade de 05/03. 4000000008 (10/03): velocidade de 10/03.
    assert linhas[4000000003].limiar_vigente_desde == date(2025, 3, 5)
    assert linhas[4000000008].limiar_vigente_desde == date(2025, 3, 10)
    # 4000000005 (07/03): hrtss com o limiar de FC de 05/03; 4000000009 (11/03): o de 10/03.
    assert linhas[4000000005].limiar_vigente_desde == date(2025, 3, 5)
    assert linhas[4000000009].limiar_vigente_desde == date(2025, 3, 10)


def test_atleta_sem_dados_de_saude_nada_estimado(session):
    atleta_id = _carrega(session, ZIP_SEM)
    rel = calcular_carga_do_atleta(session, atleta_id)
    linhas = _linhas(session)
    for id_, motivo in SEM_SAUDE.items():
        c = linhas[id_]
        assert (c.estado, c.motivo, c.carga, c.metodo) == ("sem_carga", motivo, None, None), id_
    assert rel.calculadas == TOTAIS_SEM_SAUDE["calculadas"]
    assert rel.sem_carga_total == TOTAIS_SEM_SAUDE["sem_carga_total"]
    assert rel.sem_carga == TOTAIS_SEM_SAUDE["por_motivo"]


# ---------------------------------------------------------------------------------------------
# Idempotência e recálculo
# ---------------------------------------------------------------------------------------------
def test_segunda_rodada_nao_muda_nada(session):
    atleta_id = _carrega(session)
    primeira = calcular_carga_do_atleta(session, atleta_id)
    antes = _snapshot(session)
    segunda = calcular_carga_do_atleta(session, atleta_id, agora=datetime(2030, 1, 1, tzinfo=timezone.utc))
    assert _snapshot(session) == antes  # nem id, nem calculado_em, nem entrada
    assert segunda.gravadas == 0 and segunda.inalteradas == primeira.processadas
    assert segunda.calculadas == primeira.calculadas and segunda.sem_carga == primeira.sem_carga
    assert session.scalar(select(func.count()).select_from(CargaAtividade)) == len(ESPERADO)


def test_versao_nova_recalcula_tudo(session, monkeypatch):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    antes = _snapshot(session)
    monkeypatch.setattr(cg, "VERSAO", "carga@3")
    rel = calcular_carga_do_atleta(session, atleta_id)
    depois = _linhas(session)
    assert rel.versao == "carga@3" and rel.gravadas == len(ESPERADO) and rel.inalteradas == 0
    assert all(c.versao == "carga@3" for c in depois.values())
    assert {f: v[0] for f, v in antes.items()} == {f: c.id for f, c in depois.items()}  # atualiza no lugar
    assert all(c.carga == antes[f][4] for f, c in depois.items())  # mesma conta, mesmo número


def test_limiar_novo_recalcula_so_a_nova_vigencia(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    antes = _snapshot(session)
    session.add(LimiarAtleta(atleta_id=atleta_id, grandeza="fc_bpm", valor=170.0, vigente_desde=date(2025, 3, 12),
                             origem="informado", versao_leitura="teste"))
    session.commit()
    rel = calcular_carga_do_atleta(session, atleta_id)
    depois = _snapshot(session)
    # Usam FC (todas menos natação e outra) e têm dia local a partir de 12/03.
    afetadas = {id_ for id_, e in ESPERADO.items() if e.dia >= date(2025, 3, 12) and e.modalidade != "natacao"}
    assert afetadas
    assert {f for f in depois if depois[f] != antes[f]} == afetadas
    assert rel.gravadas == len(afetadas) and rel.inalteradas == len(ESPERADO) - len(afetadas)
    # a corrida de 16/03 (4000000019) só tinha hrTSS: o limiar novo muda o número; a de 15/03 (rtss) mantém a carga
    assert depois[4000000019][4] != antes[4000000019][4]
    assert depois[4000000018][4] == antes[4000000018][4]


def test_limiar_mais_antigo_tira_a_atividade_de_sem_limiar_na_data(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    assert _linhas(session)[4000000001].motivo == "sem_limiar_na_data"
    for grandeza, valor in (("fc_bpm", 160.0), ("velocidade_ms", 3.6)):
        session.add(LimiarAtleta(atleta_id=atleta_id, grandeza=grandeza, valor=valor, vigente_desde=date(2025, 3, 1),
                                 origem="informado", versao_leitura="teste"))
    session.commit()
    calcular_carga_do_atleta(session, atleta_id)
    c = _linhas(session)[4000000001]
    assert c.estado == "calculada" and c.limiar_vigente_desde == date(2025, 3, 1)


def test_atividade_que_virou_multiesporte_perde_a_linha(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == "4000000003")).one()
    a.subtipo = "multiesporte_pai"
    session.commit()
    rel = calcular_carga_do_atleta(session, atleta_id)
    assert 4000000003 not in _linhas(session)
    assert rel.removidas == 1 and rel.ignoradas_multiesporte == TOTAIS["ignoradas_multiesporte"] + 1


def test_mudanca_nas_voltas_regrava_so_aquela_atividade(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    antes = _snapshot(session)
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == "4000000005")).one()
    a.segmentos[0].fc_media += 1
    session.commit()
    rel = calcular_carga_do_atleta(session, atleta_id)
    depois = _snapshot(session)
    assert rel.gravadas == 1 and {f for f in depois if depois[f] != antes[f]} == {4000000005}


# ---------------------------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------------------------
def test_apagar_atividade_apaga_a_carga(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == "4000000003")).one()
    session.delete(a)
    session.commit()
    assert 4000000003 not in _linhas(session)


def _base(atividade_id, **kw):
    v = dict(atividade_id=atividade_id, estado="sem_carga", motivo="sem_fc", granularidade="volta", entrada="x" * 64,
             versao="carga@2", calculado_em=datetime(2025, 1, 1, tzinfo=timezone.utc))
    v.update(kw)
    return CargaAtividade(**v)


@pytest.mark.parametrize("campos", [
    {"estado": "outro"},
    {"motivo": "sem_limiar"},  # o texto antigo da issue, fora dos seis da ADR
    {"granularidade": "bloco"},
    {"estado": "calculada", "motivo": None},  # calculada sem carga, metodo e cobertura
    {"estado": "calculada", "motivo": None, "carga": 1.0, "metodo": "trimp", "cobertura_pct": 100.0},
    {"estado": "calculada", "motivo": "sem_fc", "carga": 1.0, "metodo": "rtss", "cobertura_pct": 100.0},
    {"carga": 1.0},  # sem_carga com carga
    {"motivo": None},  # sem_carga sem motivo
])
def test_checks_rejeitam_linha_incoerente(session, campos):
    atleta_id = _carrega(session)
    a = session.scalars(select(Atividade).where(Atividade.atleta_id == atleta_id)).first()
    session.add(_base(a.id, **campos))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_atividade_id_e_unico(session):
    atleta_id = _carrega(session)
    a = session.scalars(select(Atividade).where(Atividade.atleta_id == atleta_id)).first()
    session.add(_base(a.id))
    session.flush()
    session.add(_base(a.id))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


# ---------------------------------------------------------------------------------------------
# Comando
# ---------------------------------------------------------------------------------------------
def test_comando_imprime_relatorio_so_com_contagens(fabrica, capsys):
    with fabrica() as s:
        atleta_id = _carrega(s)
    assert calcular_carga.main(["--atleta-id", str(atleta_id)]) == 0
    saida = capsys.readouterr().out
    assert f"carga carga@2 do atleta {atleta_id}" in saida
    assert "calculadas: 13" in saida and "sem carga: 7" in saida
    assert "sem_limiar_na_data: 2" in saida and "modalidade_sem_carga: 2" in saida
    assert "ignoradas (multiesporte e troca, sem linha): 3" in saida
    assert "gravadas: 20, já atualizadas: 0" in saida
    assert calcular_carga.main(["--atleta-id", str(atleta_id)]) == 0
    assert "gravadas: 0, já atualizadas: 20" in capsys.readouterr().out


def test_comando_atleta_inexistente(fabrica, capsys):
    assert calcular_carga.main(["--atleta-id", "999"]) == 1
    assert "erro" in capsys.readouterr().err


def test_comando_nao_abre_rede(fabrica, monkeypatch):
    with fabrica() as s:
        atleta_id = _carrega(s)

    def bloqueia(*a, **k):
        raise AssertionError("calcular_carga abriu conexao de rede")

    for nome in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, nome, bloqueia)
    monkeypatch.setattr(socket, "create_connection", bloqueia)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueia)
    assert calcular_carga.main(["--atleta-id", str(atleta_id)]) == 0


def test_importar_garmin_calcula_a_carga_depois_da_saude(fabrica, capsys):
    assert importar_garmin.main([str(ZIP), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert saida.index("saude limiar") < saida.index("carga carga@2") and "calculadas: 13" in saida
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(CargaAtividade)) == len(ESPERADO)


def test_erro_na_carga_vira_aviso_e_nao_derruba_a_importacao(fabrica, monkeypatch, capsys):
    def quebra(*a, **k):
        raise RuntimeError("falha qualquer 158")

    monkeypatch.setattr("worker.calcular_carga.calcular_carga_do_atleta", quebra)
    assert importar_garmin.main([str(ZIP), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert "aviso: carga nao calculada (RuntimeError)" in saida.err and "worker.calcular_carga" in saida.err
    assert "158" not in saida.err
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Atividade)) > 0
        assert s.scalar(select(func.count()).select_from(CargaAtividade)) == 0


# ---------------------------------------------------------------------------------------------
# carga@2 (#255): FC média da atividade quando nenhuma volta tem FC
# ---------------------------------------------------------------------------------------------
def test_carga2_fc_da_atividade_so_entra_na_entrada_quando_usada(session):
    atleta_id = _carrega(session)
    calcular_carga_do_atleta(session, atleta_id)
    alvo = next(i for i, e in ESPERADO.items() if e.modalidade == "ciclismo" and e.estado == "calculada"
                and e.granularidade == "volta")
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == str(alvo))).one()
    antes = _linhas(session)[alvo].entrada
    # Mudar a FC média da atividade, que tem FC nas voltas, não recalcula nada.
    a.fc_media = (a.fc_media or 140.0) + 1
    session.commit()
    rel = calcular_carga_do_atleta(session, atleta_id)
    assert rel.gravadas == 0 and _linhas(session)[alvo].entrada == antes
    # Sem FC em nenhuma volta, a FC média da atividade passa a valer e a entrada muda.
    for s in a.segmentos:
        s.fc_media = None
    a.fc_media = 150.0
    session.commit()
    rel = calcular_carga_do_atleta(session, atleta_id)
    linha = _linhas(session)[alvo]
    assert rel.gravadas == 1 and linha.entrada != antes
    assert linha.estado == "calculada" and linha.metodo == "hrtss" and linha.granularidade == "atividade"
    # Outra FC média da atividade recalcula; a conta é duração da atividade x (150/limiar)^2.
    antiga = linha.entrada
    a.fc_media = 155.0
    session.commit()
    calcular_carga_do_atleta(session, atleta_id)
    assert _linhas(session)[alvo].entrada != antiga
