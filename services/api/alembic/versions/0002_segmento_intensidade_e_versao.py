"""segmento: intensidade e versao_deteccao (ADR 0002)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INTENSIDADES = "'active', 'rest', 'warmup', 'cooldown', 'recovery', 'interval', 'other'"


def upgrade() -> None:
    # batch: o SQLite local nao adiciona CHECK com ALTER TABLE; no Postgres vira ALTER normal.
    # O nome do CHECK ('intensidade') recebe o prefixo da convencao: ck_segmento_intensidade.
    with op.batch_alter_table('segmento') as batch:
        batch.add_column(sa.Column('intensidade', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('versao_deteccao', sa.String(length=40), nullable=True))
        batch.create_check_constraint(
            'intensidade', f"intensidade IS NULL OR intensidade IN ({INTENSIDADES})"
        )


def downgrade() -> None:
    with op.batch_alter_table('segmento') as batch:
        batch.drop_constraint(op.f('ck_segmento_intensidade'), type_='check')
        batch.drop_column('versao_deteccao')
        batch.drop_column('intensidade')
