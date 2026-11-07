"""tabelas limiar_atleta e zona_fc_atleta (ADR 0010, itens 1 e 2)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-07 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'limiar_atleta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('grandeza', sa.String(length=20), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False),
        sa.Column('vigente_desde', sa.Date(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('versao_leitura', sa.String(length=40), nullable=False),
        sa.Column('importado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("grandeza IN ('fc_bpm', 'velocidade_ms')", name=op.f('ck_limiar_atleta_grandeza')),
        sa.CheckConstraint("origem IN ('garmin_export', 'informado')", name=op.f('ck_limiar_atleta_origem')),
        sa.CheckConstraint('valor > 0', name=op.f('ck_limiar_atleta_valor')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_limiar_atleta_atleta_id_atleta'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_limiar_atleta')),
        sa.UniqueConstraint('atleta_id', 'grandeza', 'origem', 'vigente_desde', name='uq_limiar_atleta_chave'),
    )
    op.create_index(op.f('ix_limiar_atleta_atleta_id'), 'limiar_atleta', ['atleta_id'], unique=False)

    op.create_table(
        'zona_fc_atleta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('esporte', sa.String(length=20), nullable=False),
        sa.Column('vigente_desde', sa.Date(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('metodo', sa.String(length=40), nullable=True),
        sa.Column('fc_max_bpm', sa.Integer(), nullable=True),
        sa.Column('fc_repouso_bpm', sa.Integer(), nullable=True),
        sa.Column('zona1_min_bpm', sa.Integer(), nullable=False),
        sa.Column('zona2_min_bpm', sa.Integer(), nullable=False),
        sa.Column('zona3_min_bpm', sa.Integer(), nullable=False),
        sa.Column('zona4_min_bpm', sa.Integer(), nullable=False),
        sa.Column('zona5_min_bpm', sa.Integer(), nullable=False),
        sa.Column('zona5_max_bpm', sa.Integer(), nullable=False),
        sa.Column('versao_leitura', sa.String(length=40), nullable=False),
        sa.Column('importado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origem IN ('garmin_export', 'garmin_fit')", name=op.f('ck_zona_fc_atleta_origem')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_zona_fc_atleta_atleta_id_atleta'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_zona_fc_atleta')),
        sa.UniqueConstraint('atleta_id', 'esporte', 'origem', 'vigente_desde', name='uq_zona_fc_atleta_chave'),
    )
    op.create_index(op.f('ix_zona_fc_atleta_atleta_id'), 'zona_fc_atleta', ['atleta_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_zona_fc_atleta_atleta_id'), table_name='zona_fc_atleta')
    op.drop_table('zona_fc_atleta')
    op.drop_index(op.f('ix_limiar_atleta_atleta_id'), table_name='limiar_atleta')
    op.drop_table('limiar_atleta')
