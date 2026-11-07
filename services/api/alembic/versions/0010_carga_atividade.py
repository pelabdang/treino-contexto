"""tabela carga_atividade (ADR 0010, item 5)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-07 21:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'carga_atividade',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atividade_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('carga', sa.Float(), nullable=True),
        sa.Column('metodo', sa.String(length=10), nullable=True),
        sa.Column('carga_rtss', sa.Float(), nullable=True),
        sa.Column('carga_hrtss', sa.Float(), nullable=True),
        sa.Column('motivo', sa.String(length=30), nullable=True),
        sa.Column('cobertura_pct', sa.Float(), nullable=True),
        sa.Column('granularidade', sa.String(length=10), nullable=False),
        sa.Column('limiar_fc_bpm', sa.Float(), nullable=True),
        sa.Column('limiar_velocidade_ms', sa.Float(), nullable=True),
        sa.Column('limiar_vigente_desde', sa.Date(), nullable=True),
        sa.Column('entrada', sa.String(length=64), nullable=False),
        sa.Column('versao', sa.String(length=40), nullable=False),
        sa.Column('calculado_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("estado IN ('calculada', 'sem_carga')", name=op.f('ck_carga_atividade_estado')),
        sa.CheckConstraint("metodo IS NULL OR metodo IN ('rtss', 'hrtss')", name=op.f('ck_carga_atividade_metodo')),
        sa.CheckConstraint(
            "motivo IS NULL OR motivo IN ('sem_dados_saude', 'sem_limiar_na_data', 'sem_fc', 'sem_pace', "
            "'cobertura_insuficiente', 'modalidade_sem_carga')",
            name=op.f('ck_carga_atividade_motivo'),
        ),
        sa.CheckConstraint("granularidade IN ('volta', 'atividade')", name=op.f('ck_carga_atividade_granularidade')),
        sa.CheckConstraint(
            "(estado = 'calculada' AND carga IS NOT NULL AND metodo IS NOT NULL AND cobertura_pct IS NOT NULL "
            "AND motivo IS NULL) OR "
            "(estado = 'sem_carga' AND motivo IS NOT NULL AND carga IS NULL AND metodo IS NULL "
            "AND carga_rtss IS NULL AND carga_hrtss IS NULL)",
            name=op.f('ck_carga_atividade_estado_campos'),
        ),
        sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_carga_atividade_atividade_id_atividade'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_carga_atividade')),
        sa.UniqueConstraint('atividade_id', name=op.f('uq_carga_atividade_atividade_id')),
    )


def downgrade() -> None:
    op.drop_table('carga_atividade')
