"""Comando worker.importar_saude e a chamada no fim do importar_garmin (issue #140, ADR 0010 item 3)."""

import os
import socket
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CargaGarminDia, LimiarAtleta, RecordePessoal, ZonaFcAtleta
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker import importar_garmin
from worker import apagar_saude
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
    assert "saude recordes: inseridas=6 atualizadas=0 ignoradas=0" in saida
    assert "saude carga: inseridas=25 atualizadas=0 ignoradas=0" in saida
    assert main([str(ZIP_SAUDE), "--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    assert "saude limiar: inseridas=0 atualizadas=0 ignoradas=5" in saida
    assert "saude zonas: inseridas=0 atualizadas=0 ignoradas=6" in saida
    assert "saude recordes: inseridas=0 atualizadas=0 ignoradas=6" in saida
    assert "saude carga: inseridas=0 atualizadas=0 ignoradas=25" in saida
    assert _conta(fabrica, LimiarAtleta) == 5 and _conta(fabrica, ZonaFcAtleta) == 6


def test_comando_nao_imprime_valores(fabrica, capsys):
    main([str(ZIP_SAUDE), "--atleta", "Ana"])
    saida = capsys.readouterr().out
    for valor in ("158", "159", "163", "3.7", "190", "1750", "8000", "248", "79.0"):
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
    assert _conta(fabrica, RecordePessoal) == _conta(fabrica, CargaGarminDia) == 0


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


def test_apagar_saude_apaga_so_as_tabelas_de_saude_do_atleta(fabrica, capsys):
    main([str(ZIP_SAUDE), "--atleta", "Ana"])
    main([str(ZIP_SAUDE), "--atleta", "Beto"])
    capsys.readouterr()
    assert apagar_saude.main(["--atleta", "Ana"]) == 0
    saida = capsys.readouterr().out
    for linha in ("limiar: apagadas=5", "zonas: apagadas=6", "recordes: apagadas=6", "carga: apagadas=25"):
        assert f"saude {linha}" in saida
    assert [_conta(fabrica, m) for m in (LimiarAtleta, ZonaFcAtleta, RecordePessoal, CargaGarminDia)] == [5, 6, 6, 25]
    assert _conta(fabrica, Atleta) == 2  # o atleta fica
    assert apagar_saude.main(["--atleta", "Ana"]) == 0  # idempotente
    assert "carga: apagadas=0" in capsys.readouterr().out


def test_apagar_saude_com_atleta_inexistente(fabrica, capsys):
    assert apagar_saude.main(["--atleta", "Ninguem"]) == 1
    assert "erro" in capsys.readouterr().err
