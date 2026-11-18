"""Protecao do CI contra travas no Postgres (issue #327): nenhum teste espera um lock para sempre.

Um teste que deixa uma sessao aberta ("idle in transaction") faz o `DROP TABLE` do teardown de outro teste esperar sem fim, e o job
`testes` fica parado no `pytest`. Com `lock_timeout`, a espera vira erro `LockNotAvailable` apontando o teste, em vez de um job de
horas. Vale so para o Postgres; o SQLite dos testes locais nao tem esse tipo de espera.
"""

from sqlalchemy import event
from sqlalchemy.engine import Engine

LOCK_TIMEOUT_S = 60


@event.listens_for(Engine, "connect")
def _lock_timeout(dbapi_conexao, _registro):
    if type(dbapi_conexao).__module__.startswith("psycopg"):
        antigo = dbapi_conexao.autocommit
        dbapi_conexao.autocommit = True
        with dbapi_conexao.cursor() as cur:
            cur.execute(f"SET lock_timeout = '{LOCK_TIMEOUT_S}s'")
        dbapi_conexao.autocommit = antigo


# ---------- e2e (pasta `tests/`) sem login (issue #500, ADR 0016, item 8) ----------
# Os e2e das Metas 1 a 12 chamam as rotas de dado do `app` em processo, sem tratar de login: para eles o atleta e o professor do caminho
# valem como os da sessao (sobrescrita de dependencia, so no `app` do teste, desfeita no fim). Nao existe variavel nem flag no servidor que
# desligue o login, e o uvicorn de verdade (subprocesso) nao recebe isto. O acesso por sessao de verdade: `services/api/tests/rotas/test_acesso.py`.

import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parent


@pytest.fixture(autouse=True)
def _e2e_sem_login(request):
    if _RAIZ / "tests" not in Path(str(request.node.fspath)).parents:
        yield
        return
    api = str(_RAIZ / "services" / "api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from app.autenticacao import PROFESSOR_INEXISTENTE, atleta_da_sessao, professor_da_sessao
    from app.db.models import Professor
    from app.db.session import get_session
    from app.main import app
    from fastapi import Depends, HTTPException

    def atleta(atleta_id: int) -> int:
        return atleta_id

    def professor(professor_id: int, session=Depends(get_session)) -> int:
        if session.get(Professor, professor_id) is None:
            raise HTTPException(status_code=404, detail=PROFESSOR_INEXISTENTE["detail"])
        return professor_id

    app.dependency_overrides[atleta_da_sessao] = atleta
    app.dependency_overrides[professor_da_sessao] = professor
    yield
    app.dependency_overrides.pop(atleta_da_sessao, None)
    app.dependency_overrides.pop(professor_da_sessao, None)
