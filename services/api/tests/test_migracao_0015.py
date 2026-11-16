"""Migracao 0015: feedback_treino.clima_visto (#409, adendo 4 da ADR 0013). Dados sinteticos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db.base import Base

from tests.test_migracao_0014 import _cfg_e_engine, _com_feedback, db_url  # noqa: F401


def _colunas(conn):
    return {c["name"] for c in inspect(conn).get_columns("feedback_treino")}


def test_0015_sobe_desce_e_sobe_de_novo_sem_tocar_nas_linhas(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0014")
    _com_feedback(engine)
    with engine.connect() as conn:
        assert "clima_visto" not in _colunas(conn)
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert "clima_visto" in _colunas(conn)
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
        # a linha de antes fica com NULL: nao entra na fila de uma vez
        assert conn.exec_driver_sql("SELECT clima_visto FROM feedback_treino").scalar() is None
    command.downgrade(cfg, "0014")
    with engine.connect() as conn:
        assert "clima_visto" not in _colunas(conn)
        assert conn.exec_driver_sql("SELECT count(*) FROM feedback_treino").scalar() == 1
        assert "recuperacao_importada_em" in _colunas(conn)  # so a coluna nova sai
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine.dispose()
