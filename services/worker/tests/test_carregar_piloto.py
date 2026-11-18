"""Comando `worker.carregar_piloto` (issue #506, ADR 0016). Dados sinteticos; as senhas temporarias so existem na saida do teste."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atleta, Conta, Professor, VinculoProfessorAtleta
from app.servicos import conta as svc
from app.servicos.professor import atletas_do_professor
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from worker import carregar_piloto

PASTA = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "professor_piloto"
AGORA = datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc)


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


def _senhas(saida):
    return dict(re.findall(r"^  (\S+@\S+)  (\S+)$", saida, flags=re.M))


def test_carrega_e_cria_uma_conta_por_professor_e_por_atleta_com_troca_obrigatoria(fabrica, capsys):
    assert carregar_piloto.main(["--fixtures", str(PASTA)]) == 0
    saida = capsys.readouterr().out
    assert "professores=2 atletas=5 vinculos=4 contas_novas=7" in saida
    senhas = _senhas(saida)
    assert len(senhas) == 7 and all(e.endswith("@piloto.exemplo.com") for e in senhas)
    with fabrica() as s:
        contas = s.scalars(select(Conta)).all()
        assert len(contas) == 7 and all(c.deve_trocar_senha and c.ativa for c in contas)
        assert sum(c.professor_id is not None for c in contas) == 2 and sum(c.atleta_id is not None for c in contas) == 5
        # as senhas servem (entram) e nao estao guardadas em claro
        for email, senha in senhas.items():
            assert senha not in {c.senha_hash for c in contas}
            conta, _ = svc.entrar(s, email, senha)
            assert conta.deve_trocar_senha is True
        s.rollback()


def test_o_consentimento_da_fixture_vale_e_so_o_atleta_consentido_aparece(fabrica, capsys):
    carregar_piloto.main(["--fixtures", str(PASTA)])
    with fabrica() as s:
        pid = s.scalars(select(Professor.id).where(Professor.nome == "Professor Fixture")).one()
        nomes = set(s.scalars(select(Atleta.nome).where(Atleta.id.in_(atletas_do_professor(pid, AGORA)))))
    assert nomes == {"Atleta Fixture Consentido"}


def test_sem_consentimento_deixa_todos_aguardando_o_atleta(fabrica, capsys):
    assert carregar_piloto.main(["--fixtures", str(PASTA), "--sem-consentimento"]) == 0
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(VinculoProfessorAtleta).where(VinculoProfessorAtleta.consentimento_em.is_not(None))) == 0
        pid = s.scalars(select(Professor.id).where(Professor.nome == "Professor Fixture")).one()
        assert list(s.scalars(select(Atleta.id).where(Atleta.id.in_(atletas_do_professor(pid, AGORA))))) == []


def test_rodar_de_novo_nao_duplica_nem_gera_senha_nova(fabrica, capsys):
    carregar_piloto.main(["--fixtures", str(PASTA)])
    capsys.readouterr()
    assert carregar_piloto.main(["--fixtures", str(PASTA)]) == 0
    saida = capsys.readouterr().out
    assert "contas_novas=0" in saida and _senhas(saida) == {} and "senha temporaria" not in saida
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Conta)) == 7
        assert s.scalar(select(func.count()).select_from(Atleta)) == 5


def test_recusa_atleta_real_com_o_mesmo_nome_e_nao_cria_conta(fabrica, capsys):
    with fabrica() as s:  # um atleta "real" (de outra assessoria) com o nome de um da fixture
        s.add(Atleta(nome="Atleta Fixture Consentido"))
        s.commit()
    assert carregar_piloto.main(["--fixtures", str(PASTA)]) == 1
    assert "erro:" in capsys.readouterr().err
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Conta)) == 0 and s.scalar(select(func.count()).select_from(Professor)) == 0


def test_dominio_invalido_e_fixture_inexistente(fabrica, capsys, tmp_path):
    assert carregar_piloto.main(["--fixtures", str(PASTA), "--dominio", "sem ponto"]) == 1
    assert carregar_piloto.main(["--fixtures", str(tmp_path)]) == 1
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Conta)) == 0


def test_senha_e_email_nao_vao_ao_log(fabrica, capsys, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    carregar_piloto.main(["--fixtures", str(PASTA)])
    saida = capsys.readouterr().out
    log = " ".join(r.getMessage() for r in caplog.records)
    for email, senha in _senhas(saida).items():
        assert senha not in log and email not in log
