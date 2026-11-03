"""atividade: inicio_lat e inicio_lon (ADR 0007)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Colunas nulas: as linhas antigas ficam NULL. batch: o SQLite local nao adiciona CHECK com ALTER TABLE.
    with op.batch_alter_table('atividade') as batch:
        batch.add_column(sa.Column('inicio_lat', sa.Float(), nullable=True))
        batch.add_column(sa.Column('inicio_lon', sa.Float(), nullable=True))
        batch.create_check_constraint('inicio_lat', "inicio_lat IS NULL OR inicio_lat BETWEEN -90 AND 90")
        batch.create_check_constraint('inicio_lon', "inicio_lon IS NULL OR inicio_lon BETWEEN -180 AND 180")
        batch.create_check_constraint('inicio_par', "(inicio_lat IS NULL) = (inicio_lon IS NULL)")


def downgrade() -> None:
    with op.batch_alter_table('atividade') as batch:
        batch.drop_constraint(op.f('ck_atividade_inicio_par'), type_='check')
        batch.drop_constraint(op.f('ck_atividade_inicio_lon'), type_='check')
        batch.drop_constraint(op.f('ck_atividade_inicio_lat'), type_='check')
        batch.drop_column('inicio_lon')
        batch.drop_column('inicio_lat')
