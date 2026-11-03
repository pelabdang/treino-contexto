"""tabela clima_atividade (ADR 0007)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-03 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'clima_atividade',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atividade_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('temperatura_c', sa.Float(), nullable=True),
        sa.Column('sensacao_c', sa.Float(), nullable=True),
        sa.Column('umidade_pct', sa.Float(), nullable=True),
        sa.Column('vento_kmh', sa.Float(), nullable=True),
        sa.Column('fonte', sa.String(length=40), nullable=True),
        sa.Column('entrada', sa.String(length=64), nullable=False),
        sa.Column('tentativas', sa.Integer(), server_default='0', nullable=False),
        sa.Column('erro', sa.String(length=200), nullable=True),
        sa.Column('consultado_em', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("estado IN ('ok', 'pendente', 'falha')", name=op.f('ck_clima_atividade_estado')),
        sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_clima_atividade_atividade_id_atividade'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_clima_atividade')),
        sa.UniqueConstraint('atividade_id', name=op.f('uq_clima_atividade_atividade_id')),
    )


def downgrade() -> None:
    op.drop_table('clima_atividade')
