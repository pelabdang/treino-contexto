"""tabela rotulo_transicao (ADR 0009, item 1)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'rotulo_transicao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atividade_id', sa.Integer(), nullable=False),
        sa.Column('transicao', sa.Boolean(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('versao_regra', sa.String(length=40), nullable=True),
        sa.Column('definido_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origem IN ('sugerido', 'atleta')", name=op.f('ck_rotulo_transicao_origem')),
        sa.CheckConstraint("(origem = 'sugerido' AND transicao AND versao_regra IS NOT NULL) OR (origem = 'atleta' AND versao_regra IS NULL)", name=op.f('ck_rotulo_transicao_origem_versao')),
        sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_rotulo_transicao_atividade_id_atividade'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_rotulo_transicao')),
        sa.UniqueConstraint('atividade_id', name=op.f('uq_rotulo_transicao_atividade_id')),
    )


def downgrade() -> None:
    op.drop_table('rotulo_transicao')
