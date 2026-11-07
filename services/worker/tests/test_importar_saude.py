"""Comando worker.importar_saude e a chamada no fim do importar_garmin (issue #140, ADR 0010 item 3)."""

import os
import socket
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, LimiarAtleta, ZonaFcAtleta
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker import importar_garmin
from worker.importar_saude import main

RAIZ = Path(__file__).resolve().parents[3]
ZIP_SAUDE = RAIZ / "tests" / "fixtures" / "garmin" / "saude" / "exportacao_saude.zip"
ZIP_SEM = RAIZ / "tests" / "fixtures" / "garmin" / "saude" / "exportacao_sem_saude.zip"
ZIP_ATIVIDADES = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def fabrica(engine, monkeypatch):
    from app.db import session as sessao
    f = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(sessao, "SessionLocal", f)
    return f


def _conta(fabrica, modelo):
    with fabrica() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def test_comando_grava_e_reexecutar_nao_duplica(fabrica, capsys):
    assert main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert "saude limiar: inseridas=5 atualizadas=0 ignoradas=0" in saida
    assert "saude zonas: inseridas=6 atualizadas=0 ignoradas=0" in saida
    assert main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert "saude limiar: inseridas=0 atualizadas=0 ignoradas=5" in saida
    assert "saude zonas: inseridas=0 atualizadas=0 ignoradas=6" in saida
    assert _conta(fabrica, LimiarAtleta) == 5 and _conta(fabrica, ZonaFcAtleta) == 6


def test_comando_nao_imprime_valores(fabrica, capsys):
    main([str(ZIP_SAUDE), "--atleta", "Ana"])
    saida = capsys.readouterr().out
    for valor in ("158", "159", "163", "3.7", "190"):
        assert valor not in saida


def test_comando_sem_dados_de_saude_nao_grava(fabrica, capsys):
    assert main([str(ZIP_SEM), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert "inseridas=0" in saida and "aviso: sem arquivo" in saida
    assert _conta(fabrica, LimiarAtleta) == _conta(fabrica, ZonaFcAtleta) == 0


def test_comando_com_caminho_inexistente(fabrica, capsys, tmp_path):
    assert main([str(tmp_path / "nao_existe.zip"), "--atleta", "Ana"]) == 1
    assert "erro" in capsys.readouterr().err


def test_comando_nao_abre_rede(fabrica, monkeypatch):
    def bloqueia(*a, **k):
        raise AssertionError("importar_saude abriu conexao de rede")

    for nome in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, nome, bloqueia)
    monkeypatch.setattr(socket, "create_connection", bloqueia)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueia)
    assert main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0


def test_importar_garmin_chama_a_saude_no_fim(fabrica, capsys):
    assert importar_garmin.main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert "saude limiar: inseridas=5" in saida
    assert _conta(fabrica, LimiarAtleta) == 5


def test_importar_garmin_sem_dados_de_saude_importa_so_as_atividades(fabrica, capsys):
    assert importar_garmin.main([str(ZIP_ATIVIDADES), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert "inseridas=5" in saida.out and "saude limiar: inseridas=0" in saida.out
    assert _conta(fabrica, Atividade) == 5 and _conta(fabrica, LimiarAtleta) == 0


def test_erro_na_saude_vira_aviso_e_nao_derruba_as_atividades(fabrica, monkeypatch, capsys):
    def quebra(*a, **k):
        raise RuntimeError("falha qualquer 158")

    monkeypatch.setattr("app.ingestao.saude.importar_saude", quebra)
    assert importar_garmin.main([str(ZIP_ATIVIDADES), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert "inseridas=5" in saida.out and _conta(fabrica, Atividade) == 5
    assert "aviso: dados de saude nao importados (RuntimeError)" in saida.err
    assert "worker.importar_saude" in saida.err and "158" not in saida.err  # so o tipo do erro, nunca a mensagem


def test_importar_garmin_sem_rede_com_saude(fabrica, monkeypatch):
    def bloqueia(*a, **k):
        raise AssertionError("abriu conexao de rede")

    for nome in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, nome, bloqueia)
    monkeypatch.setattr(socket, "create_connection", bloqueia)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueia)
    assert importar_garmin.main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0
    with Session(fabrica.kw["bind"]) as s:
        assert s.scalar(select(func.count()).select_from(LimiarAtleta)) == 5
