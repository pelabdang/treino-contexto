"""tabelas recorde_pessoal e carga_garmin_dia (ADR 0010, item 2)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-07 19:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'recorde_pessoal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('modalidade', sa.String(length=20), nullable=False),
        sa.Column('categoria', sa.String(length=60), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False),
        sa.Column('unidade', sa.String(length=10), nullable=True),
        sa.Column('alcancado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('atividade_fonte_id', sa.String(length=100), nullable=True),
        sa.Column('versao_leitura', sa.String(length=40), nullable=False),
        sa.Column('importado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("modalidade IN ('corrida', 'natacao', 'ciclismo', 'outra')", name=op.f('ck_recorde_pessoal_modalidade')),
        sa.CheckConstraint("origem IN ('garmin_export')", name=op.f('ck_recorde_pessoal_origem')),
        sa.CheckConstraint("unidade IS NULL OR unidade IN ('s', 'm', 'W', 'passos')", name=op.f('ck_recorde_pessoal_unidade')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_recorde_pessoal_atleta_id_atleta'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recorde_pessoal')),
        sa.UniqueConstraint('atleta_id', 'origem', 'modalidade', 'categoria', 'alcancado_em', name='uq_recorde_pessoal_chave'),
    )
    op.create_index(op.f('ix_recorde_pessoal_atleta_id'), 'recorde_pessoal', ['atleta_id'], unique=False)

    op.create_table(
        'carga_garmin_dia',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('dia', sa.Date(), nullable=False),
        sa.Column('carga_aguda', sa.Float(), nullable=True),
        sa.Column('carga_cronica', sa.Float(), nullable=True),
        sa.Column('razao', sa.Float(), nullable=True),
        sa.Column('versao_leitura', sa.String(length=40), nullable=False),
        sa.Column('importado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origem IN ('garmin_export')", name=op.f('ck_carga_garmin_dia_origem')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_carga_garmin_dia_atleta_id_atleta'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_carga_garmin_dia')),
        sa.UniqueConstraint('atleta_id', 'origem', 'dia', name='uq_carga_garmin_dia_chave'),
    )
    op.create_index(op.f('ix_carga_garmin_dia_atleta_id'), 'carga_garmin_dia', ['atleta_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_carga_garmin_dia_atleta_id'), table_name='carga_garmin_dia')
    op.drop_table('carga_garmin_dia')
    op.drop_index(op.f('ix_recorde_pessoal_atleta_id'), table_name='recorde_pessoal')
    op.drop_table('recorde_pessoal')
