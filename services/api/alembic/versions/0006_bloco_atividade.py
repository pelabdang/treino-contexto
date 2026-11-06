"""tabela bloco_atividade (ADR 0008, item 9)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-06 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'bloco_atividade',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atividade_id', sa.Integer(), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('categoria', sa.String(length=20), nullable=False),
        sa.Column('volta_inicial', sa.Integer(), nullable=False),
        sa.Column('volta_final', sa.Integer(), nullable=False),
        sa.Column('inicio_offset_s', sa.Float(), nullable=False),
        sa.Column('duracao_s', sa.Float(), nullable=False),
        sa.Column('parada_apos_s', sa.Float(), nullable=True),
        sa.Column('distancia_m', sa.Float(), nullable=True),
        sa.Column('fc_media', sa.Float(), nullable=True),
        sa.Column('pace_s_km', sa.Float(), nullable=True),
        sa.Column('faixa', sa.String(length=10), nullable=True),
        sa.Column('treino_chave', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('versao_deteccao', sa.String(length=40), nullable=False),
        sa.CheckConstraint("categoria IN ('esforco', 'recuperacao', 'aquecimento', 'desaquecimento', 'leve')", name=op.f('ck_bloco_atividade_categoria')),
        sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_bloco_atividade_atividade_id_atividade'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bloco_atividade')),
        sa.UniqueConstraint('atividade_id', 'ordem', name='uq_bloco_atividade_ordem'),
    )
    op.create_index(op.f('ix_bloco_atividade_atividade_id'), 'bloco_atividade', ['atividade_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bloco_atividade_atividade_id'), table_name='bloco_atividade')
    op.drop_table('bloco_atividade')
