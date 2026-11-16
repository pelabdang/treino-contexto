"""Comando `worker.carregar_professor` (issue #423, ADR 0015). Dados sinteticos."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atleta, Professor, VinculoProfessorAtleta
from app.servicos.professor import atletas_do_professor
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from worker import carregar_professor

PASTA = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "professor_piloto"
AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)


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


def test_carrega_e_so_o_atleta_consentido_aparece_para_o_professor_do_piloto(fabrica, capsys):
    assert carregar_professor.main(["--fixtures", str(PASTA)]) == 0
    saida = capsys.readouterr().out
    with fabrica() as s:
        pid = s.scalars(select(Professor.id).where(Professor.nome == "Professor Fixture")).one()
        assert f"PROFESSOR_ID={pid}" in saida and "professores=2 atletas=5 vinculos=4" in saida
        nomes = set(s.scalars(select(Atleta.nome).where(Atleta.id.in_(atletas_do_professor(pid, AGORA)))))
    assert nomes == {"Atleta Fixture Consentido"}


def test_idempotente_e_atualiza_o_consentimento(fabrica):
    assert carregar_professor.main(["--fixtures", str(PASTA)]) == 0
    with fabrica() as s:
        v = s.scalars(select(VinculoProfessorAtleta).where(VinculoProfessorAtleta.consentimento_em.is_(None))).one()
        v.consentimento_em = AGORA  # alguem consentiu
        s.commit()
    assert carregar_professor.main(["--fixtures", str(PASTA)]) == 0  # recarregar volta ao da fixture, sem duplicar
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Atleta)) == 5
        assert s.scalar(select(func.count()).select_from(Professor)) == 2
        assert s.scalar(select(func.count()).select_from(VinculoProfessorAtleta)) == 4
        assert s.scalar(select(func.count()).select_from(VinculoProfessorAtleta).where(
            VinculoProfessorAtleta.consentimento_em.is_(None))) == 1


def test_recusa_atleta_de_mesmo_nome_que_nao_e_da_fixture(fabrica, capsys):
    with fabrica() as s:
        s.add(Atleta(nome="Atleta Fixture Consentido"))
        s.commit()
    assert carregar_professor.main(["--fixtures", str(PASTA)]) == 1
    assert "nao veio desta carga" in capsys.readouterr().err
    with fabrica() as s:
        assert s.scalar(select(func.count()).select_from(Atleta)) == 1  # nada gravado
        assert s.scalar(select(func.count()).select_from(Professor)) == 0


@pytest.mark.parametrize("conteudo", ["nao e json", "{}", '{"assessoria": "A", "professores": [{"nome": "P"}], '
                                      '"professor_do_piloto": "X", "atletas": []}',
                                      '{"assessoria": "A", "professores": [{"nome": "P"}], "professor_do_piloto": "P", '
                                      '"atletas": [{"nome": "B", "vinculos": [{"professor": "P", "consentimento_em": "2026-11-01T12:00:00"}]}]}'])
def test_fixture_invalida_da_erro_claro_sem_eco_do_arquivo(tmp_path, fabrica, capsys, conteudo):
    (tmp_path / "identidade.json").write_text(conteudo, encoding="utf-8")
    assert carregar_professor.main(["--fixtures", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert err.strip() == "erro: identidade.json fora do formato esperado"


def test_pasta_sem_identidade(tmp_path, fabrica, capsys):
    assert carregar_professor.main(["--fixtures", str(tmp_path)]) == 1
    assert "identidade.json nao encontrado" in capsys.readouterr().err


def test_fixture_do_repositorio_e_json_valido_e_sintetica():
    dados = json.loads((PASTA / "identidade.json").read_text(encoding="utf-8"))
    assert all("Fixture" in a["nome"] for a in dados["atletas"])
