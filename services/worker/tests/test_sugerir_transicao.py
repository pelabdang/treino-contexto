"""Comando `worker.sugerir_transicao` e o servico por tras (issue #157, ADR 0009). Atividades sinteticas, sem rede."""

import os
from datetime import datetime, timedelta, timezone

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, RotuloTransicao
from app.servicos.transicao import aplicar_sugestao
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import worker.sugerir_transicao as cmd
from worker.sugerir_transicao import AtletaInexistente, sugerir

DIA = datetime(2030, 3, 2, tzinfo=timezone.utc)


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


def _atleta(session, nome="Atleta Ficticio"):
    a = Atleta(nome=nome)
    session.add(a)
    session.commit()
    return a


def _ativ(session, atleta, fid, modalidade, hora, min_inicio, duracao_min, dia=DIA):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id=fid, modalidade=modalidade,
        inicio=dia + timedelta(hours=hora, minutes=min_inicio), duracao_s=duracao_min * 60.0,
    )
    session.add(a)
    session.commit()
    return a


@pytest.fixture
def cenario(session):
    """Ciclismo 07:00 a 08:00 + corrida 08:02 a 08:30 (par); corrida solta a tarde; corrida solta de outro dia."""
    at = _atleta(session)
    par_a = _ativ(session, at, "a", "ciclismo", 7, 0, 60)
    par_b = _ativ(session, at, "b", "corrida", 8, 2, 28)
    solta = _ativ(session, at, "c", "corrida", 14, 0, 30)
    outro_dia = _ativ(session, at, "d", "corrida", 7, 0, 40, dia=DIA + timedelta(days=3))
    return at, par_a, par_b, solta, outro_dia


def _rotulos(session):
    return {r.atividade_id: r for r in session.scalars(select(RotuloTransicao))}


def test_treino_de_transicao_e_atividades_soltas(session, cenario):
    at, par_a, par_b, solta, outro_dia = cenario
    rel = sugerir(session, at.id)
    rotulos = _rotulos(session)
    assert set(rotulos) == {par_a.id, par_b.id}
    for r in rotulos.values():
        assert (r.transicao, r.origem, r.versao_regra) == (True, "sugerido", "transicao@1")
        assert r.definido_em is not None
    assert (rel.atividades, rel.elegiveis, rel.sugeridas, rel.inseridas) == (4, 4, 2, 2)


def test_outra_modalidade_fica_fora(session):
    at = _atleta(session)
    _ativ(session, at, "a", "ciclismo", 7, 0, 60)
    _ativ(session, at, "b", "outra", 8, 2, 28)
    rel = sugerir(session, at.id)
    assert _rotulos(session) == {}
    assert (rel.atividades, rel.elegiveis, rel.sugeridas) == (2, 1, 0)


def test_segunda_rodada_nao_muda_nada(session, cenario):
    at = cenario[0]
    sugerir(session, at.id)
    antes = {k: (r.id, r.definido_em, r.versao_regra) for k, r in _rotulos(session).items()}
    rel = sugerir(session, at.id)
    depois = {k: (r.id, r.definido_em, r.versao_regra) for k, r in _rotulos(session).items()}
    assert antes == depois
    assert (rel.inseridas, rel.atualizadas, rel.removidas, rel.mantidas) == (0, 0, 0, 2)


def test_correcao_do_atleta_nunca_e_tocada(session, cenario):
    at, par_a, par_b, solta, _ = cenario
    sugerir(session, at.id)
    agora = datetime(2030, 3, 5, tzinfo=timezone.utc)
    # o atleta diz "nao" em B (a regra sugere sim) e "sim" na solta (a regra nao sugere)
    session.execute(select(RotuloTransicao))  # noqa: B018
    rb = session.scalars(select(RotuloTransicao).where(RotuloTransicao.atividade_id == par_b.id)).one()
    rb.transicao, rb.origem, rb.versao_regra, rb.definido_em = False, "atleta", None, agora
    session.add(RotuloTransicao(atividade_id=solta.id, transicao=True, origem="atleta", definido_em=agora))
    session.commit()

    rel = sugerir(session, at.id)
    rotulos = _rotulos(session)
    assert set(rotulos) == {par_a.id, par_b.id, solta.id}
    assert (rotulos[par_b.id].transicao, rotulos[par_b.id].origem) == (False, "atleta")
    assert (rotulos[solta.id].transicao, rotulos[solta.id].origem) == (True, "atleta")
    assert rotulos[par_b.id].definido_em.replace(tzinfo=None) == agora.replace(tzinfo=None)
    assert rotulos[par_a.id].origem == "sugerido"
    assert (rel.do_atleta, rel.sugeridas_corrigidas, rel.inseridas, rel.removidas) == (2, 1, 0, 0)


def test_versao_nova_atualiza_so_as_sugeridas(session, cenario, monkeypatch):
    at, par_a, par_b, *_ = cenario
    antiga = datetime(2020, 3, 3, tzinfo=timezone.utc)
    sugerir(session, at.id)
    for r in _rotulos(session).values():
        r.versao_regra, r.definido_em = "transicao@0", antiga
    ra = session.scalars(select(RotuloTransicao).where(RotuloTransicao.atividade_id == par_b.id)).one()
    ra.transicao, ra.origem, ra.versao_regra = False, "atleta", None
    session.commit()

    rel = sugerir(session, at.id)
    rotulos = _rotulos(session)
    assert rotulos[par_a.id].versao_regra == "transicao@1"
    assert rotulos[par_a.id].definido_em.replace(tzinfo=None) > antiga.replace(tzinfo=None)
    assert rotulos[par_b.id].origem == "atleta"
    assert rel.atualizadas == 1


def test_regra_deixa_de_sugerir_e_a_linha_sugerida_sai(session, cenario):
    at, par_a, par_b, *_ = cenario
    sugerir(session, at.id)
    session.delete(session.get(Atividade, par_b.id))  # some a parte: a outra fica sem par
    session.commit()
    rel = sugerir(session, at.id)
    assert _rotulos(session) == {}
    assert rel.removidas == 1


def test_uma_atividade_nova_forma_par_com_uma_antiga(session, cenario):
    at = cenario[0]
    sugerir(session, at.id)
    # natacao logo apos a corrida solta da tarde (14:00 a 14:30)
    nova = _ativ(session, at, "e", "natacao", 14, 33, 20)
    sugerir(session, at.id)
    assert {cenario[3].id, nova.id} <= set(_rotulos(session))


def test_atletas_nao_se_misturam(session, cenario):
    outro = _atleta(session, "Outro Atleta")
    _ativ(session, outro, "z", "natacao", 7, 0, 30)  # no mesmo horario do par, mas de outro atleta
    sugerir(session, cenario[0].id)
    rel = sugerir(session, outro.id)
    assert rel.sugeridas == 0
    assert len(_rotulos(session)) == 2


def test_apagar_a_atividade_apaga_o_rotulo(session, cenario):
    at, par_a, *_ = cenario
    sugerir(session, at.id)
    session.delete(session.get(Atividade, par_a.id))
    session.commit()
    assert par_a.id not in {r.atividade_id for r in session.scalars(select(RotuloTransicao))}


def test_banco_recusa_origem_e_versao_incoerentes(session, cenario):
    a = cenario[1]
    agora = DIA
    for kwargs in (
        dict(transicao=False, origem="sugerido", versao_regra="transicao@1"),  # a regra so grava sim
        dict(transicao=True, origem="sugerido", versao_regra=None),
        dict(transicao=True, origem="atleta", versao_regra="transicao@1"),
        dict(transicao=True, origem="qualquer", versao_regra=None),
    ):
        session.add(RotuloTransicao(atividade_id=a.id, definido_em=agora, **kwargs))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_atividade_so_tem_um_rotulo(session, cenario):
    a = cenario[1]
    session.add(RotuloTransicao(atividade_id=a.id, transicao=True, origem="atleta", definido_em=DIA))
    session.commit()
    session.add(RotuloTransicao(atividade_id=a.id, transicao=False, origem="atleta", definido_em=DIA))
    with pytest.raises(IntegrityError):
        session.commit()


def test_atleta_inexistente(session):
    with pytest.raises(AtletaInexistente):
        sugerir(session, 999)


def test_relatorio_do_comando(session, cenario):
    texto = cmd.formatar(sugerir(session, cenario[0].id), cenario[0].id)
    assert "transicao@1" in texto
    assert "sugeridas pela regra: 2" in texto
    assert "inseridas: 2" in texto
    assert session.scalar(select(func.count()).select_from(RotuloTransicao)) == 2


def test_main_atleta_inexistente(engine, monkeypatch, capsys):
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))
    assert cmd.main(["--atleta-id", "999"]) == 1
    assert "não encontrado" in capsys.readouterr().err


def test_main_imprime_relatorio(engine, session, cenario, monkeypatch, capsys):
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))
    assert cmd.main(["--atleta-id", str(cenario[0].id)]) == 0
    assert "sugeridas pela regra: 2" in capsys.readouterr().out


def test_servico_aceita_o_relogio_injetado(session, cenario):
    agora = datetime(2031, 1, 1, tzinfo=timezone.utc)
    aplicar_sugestao(session, cenario[0].id, agora=agora)
    assert {r.definido_em.replace(tzinfo=None) for r in _rotulos(session).values()} == {agora.replace(tzinfo=None)}


def _importada(fid, modalidade, inicio, duracao_min):
    from app.ingestao.garmin.modelos import AtividadeImportada

    return AtividadeImportada(
        fonte_id=fid, modalidade=modalidade, inicio=inicio, duracao_s=duracao_min * 60.0,
        distancia_m=1000.0, fc_media=None, arquivo_bruto=None,
    )


def test_importacao_ja_sugere_e_reimportar_nao_muda(session, monkeypatch):
    """A importacao chama a sugestao do atleta inteiro; reimportar a mesma exportacao deixa o mesmo banco."""
    from app.ingestao import importacao

    lista = [
        _importada("1", "ciclismo", DIA + timedelta(hours=7), 60),
        _importada("2", "corrida", DIA + timedelta(hours=8, minutes=2), 28),
        _importada("3", "corrida", DIA + timedelta(hours=14), 30),
    ]
    monkeypatch.setattr(importacao, "ler_exportacao", lambda caminho: lista)
    importacao.importar(session, "ignorado", "Atleta Ficticio")
    primeiro = {r.id: r.definido_em for r in _rotulos(session).values()}
    assert len(primeiro) == 2
    importacao.importar(session, "ignorado", "Atleta Ficticio")
    assert {r.id: r.definido_em for r in _rotulos(session).values()} == primeiro


def test_erro_na_sugestao_nao_derruba_a_importacao(session, monkeypatch):
    from app.ingestao import importacao

    def quebra(*a, **k):
        raise RuntimeError("falha de teste")

    monkeypatch.setattr(importacao, "ler_exportacao", lambda caminho: [_importada("1", "corrida", DIA, 30)])
    monkeypatch.setattr(importacao, "aplicar_sugestao", quebra)
    rel = importacao.importar(session, "ignorado", "Atleta Ficticio")
    assert rel.inseridas == 1
