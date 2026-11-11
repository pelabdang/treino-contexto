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
