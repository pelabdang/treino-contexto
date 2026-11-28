"""Migracao 0019: conversa e mensagem do chat (#597, ADR 0017). Dados sinteticos."""

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from tests.test_migracao_0014 import _cfg_e_engine, db_url  # noqa: F401


def _tabelas(conn):
    return set(inspect(conn).get_table_names())


def _base(conn):
    conn.exec_driver_sql("INSERT INTO atleta (id, nome) VALUES (1, 'Atleta Teste')")
    conn.exec_driver_sql("INSERT INTO conta (id, email, senha_hash, atleta_id) VALUES (1, 'a@exemplo.test', 'h', 1)")
    conn.exec_driver_sql("INSERT INTO conversa (id, atleta_id, dono_conta_id, titulo) VALUES (1, 1, 1, 'Como foi a semana?')")


def _msg(conn, ordem, estado, resposta, motivo):
    # `text()` com parametros nomeados vale no SQLite e no Postgres (`?` so existe no SQLite)
    conn.execute(sa.text(
        "INSERT INTO mensagem (conversa_id, ordem, pergunta, chamadas_ferramenta, resposta, estado, motivo, versao_checagens, versao_prompt)"
        " VALUES (1, :ordem, 'p', '[]', :resposta, :estado, :motivo, 'checagens_chat@1', 'prompt_chat@1')"),
        {"ordem": ordem, "resposta": resposta, "estado": estado, "motivo": motivo})


def test_0019_sobe_desce_e_sobe_de_novo(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "0018")
    with engine.connect() as conn:
        assert not {"conversa", "mensagem"} & _tabelas(conn)
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert {"conversa", "mensagem"} <= _tabelas(conn)
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    command.downgrade(cfg, "0018")
    with engine.connect() as conn:
        assert not {"conversa", "mensagem"} & _tabelas(conn)
        assert "atleta" in _tabelas(conn)
    command.upgrade(cfg, "head")


def test_0019_checks_do_estado_e_da_ordem(db_url):  # noqa: F811
    cfg, engine = _cfg_e_engine(db_url)
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        _base(conn)
        _msg(conn, 1, "respondida", "texto", None)
        _msg(conn, 2, "recusada", "texto fixo", "fora_do_tema")
        _msg(conn, 3, "reprovada", None, "texto_reprovado")
        _msg(conn, 4, "erro", None, "tempo_limite")
    for ordem, estado, resposta, motivo in [
        (5, "respondida", None, None),             # respondida sem resposta
        (5, "respondida", "t", "x"),               # respondida com motivo
        (5, "reprovada", "texto proibido", "m"),   # reprovada nunca guarda o texto
        (5, "erro", None, None),                   # erro sem motivo
        (5, "recusada", None, "fora_do_tema"),     # recusada sem o texto fixo
        (5, "inventado", None, "m"),
        (1, "respondida", "t", None),              # ordem repetida
    ]:
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                _msg(conn, ordem, estado, resposta, motivo)
