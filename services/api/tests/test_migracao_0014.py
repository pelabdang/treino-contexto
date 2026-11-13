"""Migracao 0014: recuperacao_dia e feedback_treino.recuperacao_importada_em (ADR 0014, item 1). Dados sinteticos."""

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
_DATA = "'2026-11-10 12:00:00'"


@pytest.fixture
def db_url(tmp_path):
    return os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'mig.db'}"


def _cfg_e_engine(db_url):
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = db_url
    engine = create_engine(db_url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    return cfg, engine


_RD = ("INSERT INTO recuperacao_dia (atleta_id, origem, noite, sono_s, vfc_ms, fc_repouso_bpm, versao_leitura, importado_em) "
       "VALUES ({v})")


def _rd(conn, atleta=1, origem="'garmin_connect'", noite="'2026-03-10'", sono="25000", vfc="90.0", fc="55"):
    conn.exec_driver_sql(_RD.format(v=f"{atleta}, {origem}, {noite}, {sono}, {vfc}, {fc}, 'recuperacao_leitura@1', {_DATA}"))


def _com_feedback(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Ana')")
        conn.exec_driver_sql("INSERT INTO atividade (id, atleta_id, fonte, fonte_id, modalidade, inicio, duracao_s) "
                             "VALUES (1, 1, 't', '1', 'corrida', '2026-11-10 10:00:00', 1800)")
        conn.exec_driver_sql(
            "INSERT INTO checkin_treino (id, atividade_id, pse, sensacao, nada_a_relatar, dor, cansaco, sono_ruim, calor, "
            f"trabalho_estresse, versao, registrado_em, atualizado_em) VALUES (1, 1, 5, 3, TRUE, FALSE, FALSE, FALSE, FALSE, "
            f"FALSE, 'checkin@1', {_DATA}, {_DATA})")
        conn.exec_driver_sql(
            "INSERT INTO feedback_treino (checkin_id, estado, texto, versao_fatos, versao_prompt, versao_checagens, provedor, "
            f"modelo, tentativas, checkin_atualizado_em, tentado_em) VALUES (1, 'pronto', 'tres linhas', 'fatos_treino@1', "
            f"'feedback_prompt@1', 'checagens_feedback@1', 'falso', 'falso', 1, {_DATA}, {_DATA})")


def test_0014_cria_a_tabela_e_os_check_rejeitam_o_invalido(db_url):
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Ana')")
        _rd(conn)
    with engine.begin() as conn:  # cada medida e independente
        _rd(conn, noite="'2026-03-11'", sono="NULL", vfc="NULL")
        _rd(conn, noite="'2026-03-12'", vfc="NULL", fc="NULL")
    ruins = {
        "as tres medidas nulas": dict(sono="NULL", vfc="NULL", fc="NULL"),
        "sono zero": dict(sono="0"),
        "sono acima de 24 h": dict(sono="86401"),
        "vfc zero": dict(vfc="0"),
        "vfc acima de 500": dict(vfc="500.1"),
        "fc de repouso zero": dict(fc="0"),
        "fc de repouso 19": dict(fc="19"),
        "fc de repouso 151": dict(fc="151"),
        "origem desconhecida": dict(origem="'garmin_export'"),
    }
    for kw in ruins.values():
        with pytest.raises(IntegrityError), engine.begin() as conn:
            _rd(conn, noite="'2026-04-01'", **kw)
    with engine.begin() as conn:  # os extremos passam
        _rd(conn, noite="'2026-04-02'", sono="1", vfc="500", fc="20")
        _rd(conn, noite="'2026-04-03'", sono="86400", vfc="0.1", fc="150")
    with pytest.raises(IntegrityError), engine.begin() as conn:  # UNIQUE (atleta, origem, noite)
        _rd(conn)
    if engine.dialect.name == "postgresql":  # o SQLite dos testes nao aplica FK sem o PRAGMA
        with pytest.raises(IntegrityError), engine.begin() as conn:
            _rd(conn, atleta=99, noite="'2026-05-01'")
    command.downgrade(cfg, "base")
    engine.dispose()


def test_0014_downgrade_remove_so_o_novo_e_sobe_de_novo(db_url):
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    _com_feedback(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(f"UPDATE feedback_treino SET recuperacao_importada_em = {_DATA}")
        _rd(conn)
    command.downgrade(cfg, "0013")
    with engine.connect() as conn:
        insp = inspect(conn)
        assert "recuperacao_dia" not in insp.get_table_names()
        assert "recuperacao_importada_em" not in {c["name"] for c in insp.get_columns("feedback_treino")}
        assert conn.exec_driver_sql("SELECT count(*) FROM feedback_treino").scalar() == 1  # o feedback fica
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
        assert conn.exec_driver_sql("SELECT recuperacao_importada_em FROM feedback_treino").scalar() is None
    command.downgrade(cfg, "base")
    engine.dispose()
