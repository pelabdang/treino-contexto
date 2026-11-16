"""Migracao 0016: atividade.tipo_confirmado_por/_em e feedback_treino.tipo_visto (#423, ADR 0015, item 1). Dados sinteticos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect

from app.db.base import Base

from tests.test_migracao_0014 import _cfg_e_engine, _com_feedback, db_url  # noqa: F401

_FK = "fk_atividade_tipo_confirmado_por"


def _colunas(conn, tabela):
    return {c["name"] for c in inspect(conn).get_columns(tabela)}


def test_0016_sobe_desce_e_sobe_de_novo_sem_tocar_nas_linhas(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0015")
    _com_feedback(engine)
    with engine.connect() as conn:
        assert "tipo_confirmado_por" not in _colunas(conn, "atividade")
        assert "tipo_visto" not in _colunas(conn, "feedback_treino")
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert {"tipo_confirmado_por", "tipo_confirmado_em"} <= _colunas(conn, "atividade")
        assert "tipo_visto" in _colunas(conn, "feedback_treino")
        fks = {fk["name"]: fk for fk in inspect(conn).get_foreign_keys("atividade")}
        assert _FK in fks and fks[_FK]["referred_table"] == "professor"
        assert fks[_FK]["options"].get("ondelete") == "SET NULL"
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
        # as linhas de antes ficam com NULL nas tres colunas
        assert tuple(conn.exec_driver_sql("SELECT tipo_confirmado_por, tipo_confirmado_em FROM atividade").one()) == (None, None)
        assert conn.exec_driver_sql("SELECT tipo_visto FROM feedback_treino").scalar() is None
    command.downgrade(cfg, "0015")
    with engine.connect() as conn:
        assert not ({"tipo_confirmado_por", "tipo_confirmado_em"} & _colunas(conn, "atividade"))
        assert "tipo_visto" not in _colunas(conn, "feedback_treino")
        assert _FK not in {fk["name"] for fk in inspect(conn).get_foreign_keys("atividade")}
        assert conn.exec_driver_sql("SELECT count(*) FROM atividade").scalar() == 1
        assert conn.exec_driver_sql("SELECT count(*) FROM feedback_treino").scalar() == 1
        assert "clima_visto" in _colunas(conn, "feedback_treino")  # so o que a 0016 criou sai
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine.dispose()


def test_0016_apagar_o_professor_zera_so_o_tipo_confirmado_por(db_url):  # noqa: F811
    """`ON DELETE SET NULL`. No SQLite o `PRAGMA foreign_keys` precisa estar ligado; no Postgres vale sempre."""
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
        conn.exec_driver_sql(
            "INSERT INTO atividade (id, atleta_id, fonte, fonte_id, modalidade, inicio, duracao_s, tipo_treino, tipo_origem, "
            "tipo_confirmado, tipo_confirmado_por, tipo_confirmado_em) VALUES (1, 1, 't', '1', 'corrida', "
            "'2026-11-10 10:00:00', 1800, 'leve', 'professor', TRUE, 7, '2026-11-10 12:00:00')")
    with eng.begin() as conn:
        conn.exec_driver_sql("DELETE FROM professor WHERE id = 7")
    with eng.connect() as conn:
        linha = conn.exec_driver_sql(
            "SELECT tipo_confirmado_por, tipo_confirmado, tipo_treino, tipo_origem, tipo_confirmado_em IS NOT NULL "
            "FROM atividade WHERE id = 1").one()
    assert linha[0] is None  # o "quem" some
    assert bool(linha[1]) is True and linha[2] == "leve" and linha[3] == "professor" and bool(linha[4])  # o resto fica
    eng.dispose()
