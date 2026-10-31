"""atividade: fuso_min (ADR 0003)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31 20:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch: o SQLite local nao adiciona CHECK com ALTER TABLE; no Postgres vira ALTER normal.
    # O CHECK 'fuso_min' recebe o prefixo da convencao: ck_atividade_fuso_min.
    with op.batch_alter_table('atividade') as batch:
        batch.add_column(sa.Column('fuso_min', sa.Integer(), nullable=True))
        batch.create_check_constraint('fuso_min', "fuso_min IS NULL OR fuso_min BETWEEN -720 AND 840")


def downgrade() -> None:
    with op.batch_alter_table('atividade') as batch:
        batch.drop_constraint(op.f('ck_atividade_fuso_min'), type_='check')
        batch.drop_column('fuso_min')
