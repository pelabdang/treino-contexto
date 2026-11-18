"""Migracao 0017: conta, sessao, tentativa_login, consentimento_evento e colunas do vinculo (#499, ADR 0016, item 1). Dados sinteticos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
import pytest

from app.db.base import Base

from tests.test_migracao_0014 import _cfg_e_engine, db_url  # noqa: F401

NOVAS = {"conta", "sessao", "tentativa_login", "consentimento_evento"}


def _colunas(conn, tabela):
    return {c["name"] for c in inspect(conn).get_columns(tabela)}


def test_0017_sobe_desce_e_sobe_de_novo_sem_tocar_nas_linhas(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0016")
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO assessoria (id, nome) VALUES (1, 'Assessoria Teste')")
        conn.exec_driver_sql("INSERT INTO professor (id, assessoria_id, nome) VALUES (7, 1, 'Professor Teste')")
        conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Ana')")
        conn.exec_driver_sql("INSERT INTO vinculo_professor_atleta (professor_id, atleta_id, consentimento_em) "
                             "VALUES (7, 1, '2026-11-10 10:00:00')")
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert NOVAS <= set(inspect(conn).get_table_names())
        assert {"termo_versao", "consentimento_revogado_em"} <= _colunas(conn, "vinculo_professor_atleta")
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
        v = conn.exec_driver_sql("SELECT termo_versao, consentimento_revogado_em, consentimento_em IS NOT NULL "
                                 "FROM vinculo_professor_atleta").one()
        assert v[0] is None and v[1] is None and bool(v[2])
    command.downgrade(cfg, "0016")
    with engine.connect() as conn:
        assert not (NOVAS & set(inspect(conn).get_table_names()))
        assert not ({"termo_versao", "consentimento_revogado_em"} & _colunas(conn, "vinculo_professor_atleta"))
        assert conn.exec_driver_sql("SELECT count(*) FROM vinculo_professor_atleta").scalar() == 1
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine.dispose()


def test_0017_um_papel_por_conta_email_unico_e_cascata_da_sessao(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    engine.dispose()
    eng = create_engine(db_url)
    if eng.dialect.name == "sqlite":
        event.listen(eng, "connect", lambda c, _r: c.execute("PRAGMA foreign_keys=ON"))
    with eng.begin() as conn:
        conn.exec_driver_sql("INSERT INTO assessoria (id, nome) VALUES (1, 'Assessoria Teste')")
        conn.exec_driver_sql("INSERT INTO professor (id, assessoria_id, nome) VALUES (7, 1, 'Professor Teste')")
        conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Ana')")
        conn.exec_driver_sql("INSERT INTO conta (id, email, senha_hash, atleta_id) VALUES (1, 'a@exemplo.com', 'x', 1)")
        conn.exec_driver_sql("INSERT INTO sessao (conta_id, token_hash, criada_em, expira_em) "
                             "VALUES (1, 'h1', '2026-11-17 10:00:00', '2026-12-17 10:00:00')")
    for sql in (
        "INSERT INTO conta (id, email, senha_hash, atleta_id, professor_id) VALUES (2, 'b@exemplo.com', 'x', 1, 7)",  # dois papeis
        "INSERT INTO conta (id, email, senha_hash) VALUES (2, 'b@exemplo.com', 'x')",  # nenhum papel
        "INSERT INTO conta (id, email, senha_hash, professor_id) VALUES (2, 'a@exemplo.com', 'x', 7)",  # e-mail repetido
        "INSERT INTO conta (id, email, senha_hash, atleta_id) VALUES (2, 'b@exemplo.com', 'x', 1)",  # atleta com duas contas
    ):
        with pytest.raises(IntegrityError):
            with eng.begin() as conn:
                conn.exec_driver_sql(sql)
    with eng.begin() as conn:
        conn.exec_driver_sql("DELETE FROM conta WHERE id = 1")
    with eng.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM sessao").scalar() == 0  # ON DELETE CASCADE
    eng.dispose()
