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


@pytest.fixture(autouse=True)
def _cliente_http_do_teste_sem_log_de_url():
    """O LiteLLM traz o `openai` 3.x, que traz o `httpx2`; o `TestClient` do Starlette passa a usar o `httpx2`, que registra
    cada URL (com a query) no logger `httpx2` em INFO. E log do cliente DO TESTE, nao da API; sem isso os testes que conferem
    "nada do dado no log" (caplog em DEBUG) veriam a URL que o proprio teste montou."""
    import logging

    logger = logging.getLogger("httpx2")
    antes = logger.level
    logger.setLevel(logging.WARNING)
    yield
    logger.setLevel(antes)
