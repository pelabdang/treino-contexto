"""Comandos do operador `worker.conta` (issue #499, ADR 0016, item 6). Dados sinteticos."""

import io
import os

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Assessoria, Atleta, Conta, Professor, VinculoProfessorAtleta
from app.servicos import conta as svc
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from worker import conta as cmd

SENHA = "senha-de-teste-123"


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
    with f() as s:
        a = Assessoria(nome="Assessoria Teste")
        s.add(a)
        s.flush()
        s.add_all([Atleta(nome="Ana Teste", assessoria_id=a.id), Professor(nome="Paulo Teste", assessoria_id=a.id)])
        s.commit()
    return f


def test_criar_com_senha_pela_entrada_padrao(fabrica, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    assert cmd.main(["criar", "--email", "Ana@Exemplo.com", "--atleta", "1", "--senha-stdin"]) == 0
    out = capsys.readouterr()
    assert SENHA not in out.out + out.err
    with fabrica() as s:
        c = s.scalars(select(Conta)).one()
        assert c.email == "ana@exemplo.com" and c.atleta_id == 1 and not c.deve_trocar_senha and SENHA not in c.senha_hash


def test_criar_com_senha_temporaria_obriga_a_troca_e_mostra_uma_vez(fabrica, capsys):
    assert cmd.main(["criar", "--email", "p@exemplo.com", "--professor", "1", "--gerar-senha-temporaria"]) == 0
    saida = capsys.readouterr().out
    temp = saida.split(": ")[-1].strip()
    with fabrica() as s:
        c = s.scalars(select(Conta)).one()
        assert c.deve_trocar_senha and c.professor_id == 1
        conta, _ = svc.entrar(s, "p@exemplo.com", temp)
        assert conta.id == c.id


def test_senha_fraca_e_recusada_com_codigo_2(fabrica, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("curta\n"))
    assert cmd.main(["criar", "--email", "a@exemplo.com", "--atleta", "1", "--senha-stdin"]) == 2
    assert "curta" not in capsys.readouterr().err


def test_erros_de_operador_sao_mensagem_fixa_sem_email(fabrica, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    assert cmd.main(["criar", "--email", "a@exemplo.com", "--atleta", "99", "--senha-stdin"]) == 1
    assert "a@exemplo.com" not in capsys.readouterr().err
    assert cmd.main(["redefinir-senha", "--email", "naoexiste@exemplo.com"]) == 1
    assert "naoexiste" not in capsys.readouterr().err


def test_vincular_nao_da_consentimento(fabrica, capsys):
    assert cmd.main(["vincular", "--professor", "1", "--atleta", "1"]) == 0
    assert cmd.main(["vincular", "--professor", "1", "--atleta", "1"]) == 0  # idempotente
    with fabrica() as s:
        v = s.scalars(select(VinculoProfessorAtleta)).one()
        assert v.consentimento_em is None and v.termo_versao is None
    assert cmd.main(["vincular", "--professor", "9", "--atleta", "1"]) == 1


def test_redefinir_desativar_e_limpar(fabrica, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(SENHA + "\n"))
    cmd.main(["criar", "--email", "a@exemplo.com", "--atleta", "1", "--senha-stdin"])
    capsys.readouterr()
    assert cmd.main(["redefinir-senha", "--email", "a@exemplo.com"]) == 0
    temp = capsys.readouterr().out.split(": ")[-1].strip()
    with fabrica() as s:
        assert svc.conta_por_email(s, "a@exemplo.com").deve_trocar_senha
        svc.entrar(s, "a@exemplo.com", temp)
        s.commit()
    assert cmd.main(["desativar", "--email", "a@exemplo.com"]) == 0
    with fabrica() as s:
        with pytest.raises(svc.CredencialInvalida):
            svc.entrar(s, "a@exemplo.com", temp)
    assert cmd.main(["limpar"]) == 0
