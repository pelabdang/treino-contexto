"""A migração Alembic tem que gerar o mesmo esquema que os modelos."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

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
