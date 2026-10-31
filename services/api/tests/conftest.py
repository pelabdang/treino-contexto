import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401
from app.db.base import Base

# Em CI a variável TEST_DATABASE_URL aponta para o Postgres do serviço.
# Localmente, sem Postgres, os testes usam SQLite em memória.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
