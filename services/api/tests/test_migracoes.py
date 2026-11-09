"""A migração Alembic tem que gerar o mesmo esquema que os modelos."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.db.base import Base

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_url(tmp_path):
    return os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'mig.db'}"


def test_upgrade_e_downgrade_sem_diferenca(db_url):
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = db_url
    engine = create_engine(db_url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")

    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []

    command.downgrade(cfg, "base")
    engine.dispose()


def _cfg_e_engine(db_url):
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = db_url
    engine = create_engine(db_url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    return cfg, engine


_BASE = (
    "INSERT INTO atividade (atleta_id, fonte, fonte_id, modalidade, inicio, duracao_s, tipo_treino, tipo_origem{cols}) "
    "VALUES (1, 'teste', '{fid}', 'corrida', '2026-03-03 10:00:00', 1800, {tipo}, {origem}{vals})"
)


def _aspas(v):
    return "NULL" if v is None else f"'{v}'"


def _inserir(conn, fid, tipo, origem, divergencia=None, versao=None, nova=True):
    cols, vals = (", tipo_versao, tipo_divergencia", f", {_aspas(versao)}, {_aspas(divergencia)}") if nova else ("", "")
    conn.exec_driver_sql(_BASE.format(fid=fid, tipo=_aspas(tipo), origem=_aspas(origem), cols=cols, vals=vals))


def _colunas_de_atividade(conn):
    return {c["name"] for c in inspect(conn).get_columns("atividade")}


def test_0011_constraints_novas_e_downgrade_zera_so_o_derivado(db_url):
    """0011 aceita `semana_padrao` e rejeita divergencia fora dela; o downgrade zera so as linhas `semana_padrao`."""
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0010")
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Ana')")
        _inserir(conn, "antiga", "intervalado", "sugestao", nova=False)
    with pytest.raises(IntegrityError), engine.begin() as conn:  # antes da 0011 a origem nova nao existe
        _inserir(conn, "x", "leve", "semana_padrao", nova=False)

    command.upgrade(cfg, "0011")
    with engine.begin() as conn:  # a linha antiga segue intacta, sem versao nem divergencia (nada e preenchido)
        assert conn.exec_driver_sql("SELECT tipo_treino, tipo_origem, tipo_versao, tipo_divergencia FROM atividade").one() == (
            "intervalado", "sugestao", None, None)
        _inserir(conn, "plano", "intervalado", "semana_padrao", "sem_esforco", "tipo_treino@1")
        _inserir(conn, "confirmada", "fartlek", "professor")
    for origem, div in [("professor", "tem_tiros"), (None, "tem_tiros"), ("semana_padrao", "outro")]:
        with pytest.raises(IntegrityError), engine.begin() as conn:  # divergencia sem a origem; motivo fora da lista
            _inserir(conn, "ruim", "leve", origem, div)

    command.downgrade(cfg, "0010")
    with engine.begin() as conn:
        linhas = {r[0]: (r[1], r[2]) for r in conn.exec_driver_sql("SELECT fonte_id, tipo_treino, tipo_origem FROM atividade").all()}
        assert linhas == {"antiga": ("intervalado", "sugestao"), "plano": (None, None), "confirmada": ("fartlek", "professor")}
        assert not {"tipo_versao", "tipo_divergencia"} & _colunas_de_atividade(conn)
        assert not {"semana_padrao", "semana_padrao_item"} & set(inspect(conn).get_table_names())
    with pytest.raises(IntegrityError), engine.begin() as conn:  # o CHECK antigo voltou
        _inserir(conn, "y", "leve", "semana_padrao", nova=False)
    command.downgrade(cfg, "base")
    engine.dispose()


def test_0011_sobe_de_novo_depois_de_descer(db_url):
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0010")
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    command.downgrade(cfg, "base")
    engine.dispose()
