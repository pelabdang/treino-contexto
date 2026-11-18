"""Migracao 0018: feedback_treino.transicao_visto (#510). Dados sinteticos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect

from tests.test_migracao_0014 import _cfg_e_engine, _com_feedback, db_url  # noqa: F401


def _colunas(conn, tabela):
    return {c["name"] for c in inspect(conn).get_columns(tabela)}


def test_0018_sobe_desce_e_sobe_de_novo_sem_tocar_nas_linhas(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0017")
    _com_feedback(engine)
    with engine.connect() as conn:
        assert "transicao_visto" not in _colunas(conn, "feedback_treino")
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert "transicao_visto" in _colunas(conn, "feedback_treino")
        assert conn.exec_driver_sql("SELECT transicao_visto FROM feedback_treino").scalar() is None  # linha de antes: NULL
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    command.downgrade(cfg, "0017")
    with engine.connect() as conn:
        assert "transicao_visto" not in _colunas(conn, "feedback_treino")
        assert conn.exec_driver_sql("SELECT count(*) FROM feedback_treino").scalar() == 1
        assert "tipo_visto" in _colunas(conn, "feedback_treino")
    command.upgrade(cfg, "head")
