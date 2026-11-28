"""Migracao 0020: mensagem.avaliacao e avaliada_em (adendo 17 da ADR 0004). Dados sinteticos."""

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from tests.test_migracao_0014 import _cfg_e_engine, db_url  # noqa: F401
from tests.test_migracao_0019 import _base, _msg


def _colunas(conn):
    return {c["name"] for c in inspect(conn).get_columns("mensagem")}


def test_0020_sobe_desce_e_sobe_sem_tocar_nas_linhas(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0019")
    with engine.begin() as conn:
        _base(conn)
        _msg(conn, 1, "respondida", "texto", None)
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert {"avaliacao", "avaliada_em"} <= _colunas(conn)
        assert conn.execute(sa.text("SELECT avaliacao, avaliada_em FROM mensagem")).one() == (None, None)  # linha de antes: NULL
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    command.downgrade(cfg, "0019")
    with engine.connect() as conn:
        assert not {"avaliacao", "avaliada_em"} & _colunas(conn)
        assert conn.execute(sa.text("SELECT count(*) FROM mensagem")).scalar() == 1
    command.upgrade(cfg, "head")


def test_0020_checks_da_avaliacao(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        _base(conn)
        _msg(conn, 1, "respondida", "texto", None)
        _msg(conn, 2, "erro", None, "provedor_erro")
        conn.execute(sa.text("UPDATE mensagem SET avaliacao = -1, avaliada_em = '2030-03-15 12:00:00' WHERE ordem = 1"))
    for sql in ("UPDATE mensagem SET avaliacao = 2, avaliada_em = '2030-03-15 12:00:00' WHERE ordem = 1",   # fora de -1/1
                "UPDATE mensagem SET avaliacao = 1, avaliada_em = NULL WHERE ordem = 1",                     # sem data
                "UPDATE mensagem SET avaliada_em = '2030-03-15 12:00:00', avaliacao = NULL WHERE ordem = 1",  # data sem valor
                "UPDATE mensagem SET avaliacao = 1, avaliada_em = '2030-03-15 12:00:00' WHERE ordem = 2"):    # so respondida
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(sa.text(sql))
