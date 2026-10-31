"""modelo de dados minimo

Revision ID: 0001
Revises: (nenhuma)
Create Date: 2026-10-31 16:41:07.282515
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.create_table('assessoria',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=200), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assessoria'))
    )
    op.create_table('atleta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assessoria_id', sa.Integer(), nullable=True),
    sa.Column('nome', sa.String(length=200), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['assessoria_id'], ['assessoria.id'], name=op.f('fk_atleta_assessoria_id_assessoria')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_atleta'))
    )
    op.create_table('professor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assessoria_id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=200), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['assessoria_id'], ['assessoria.id'], name=op.f('fk_professor_assessoria_id_assessoria')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_professor'))
    )
    op.create_table('atividade',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('atleta_id', sa.Integer(), nullable=False),
    sa.Column('fonte', sa.String(length=40), nullable=False),
    sa.Column('fonte_id', sa.String(length=100), nullable=False),
    sa.Column('modalidade', sa.String(length=20), nullable=False),
    sa.Column('subtipo', sa.String(length=60), nullable=True),
    sa.Column('inicio', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duracao_s', sa.Float(), nullable=False),
    sa.Column('distancia_m', sa.Float(), nullable=True),
    sa.Column('fc_media', sa.Float(), nullable=True),
    sa.Column('tipo_treino', sa.String(length=20), nullable=True),
    sa.Column('tipo_origem', sa.String(length=20), nullable=True),
    sa.Column('tipo_confirmado', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('arquivo_bruto', sa.String(length=500), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("modalidade IN ('corrida', 'natacao', 'ciclismo', 'outra')", name=op.f('ck_atividade_modalidade')),
    sa.CheckConstraint("tipo_origem IS NULL OR tipo_origem IN ('sugestao', 'professor', 'trainingpeaks')", name=op.f('ck_atividade_tipo_origem')),
    sa.CheckConstraint("tipo_treino IS NULL OR tipo_treino IN ('leve', 'moderado', 'longo', 'intervalado', 'fartlek')", name=op.f('ck_atividade_tipo_treino')),
    sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_atividade_atleta_id_atleta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_atividade')),
    sa.UniqueConstraint('atleta_id', 'fonte', 'fonte_id', name='uq_atividade_origem')
    )
    op.create_index(op.f('ix_atividade_atleta_id'), 'atividade', ['atleta_id'], unique=False)
    op.create_index(op.f('ix_atividade_inicio'), 'atividade', ['inicio'], unique=False)
    op.create_table('vinculo_professor_atleta',
    sa.Column('professor_id', sa.Integer(), nullable=False),
    sa.Column('atleta_id', sa.Integer(), nullable=False),
    sa.Column('consentimento_em', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_vinculo_professor_atleta_atleta_id_atleta')),
    sa.ForeignKeyConstraint(['professor_id'], ['professor.id'], name=op.f('fk_vinculo_professor_atleta_professor_id_professor')),
    sa.PrimaryKeyConstraint('professor_id', 'atleta_id', name=op.f('pk_vinculo_professor_atleta'))
    )
    op.create_table('segmento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('atividade_id', sa.Integer(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('inicio_offset_s', sa.Float(), nullable=True),
    sa.Column('duracao_s', sa.Float(), nullable=False),
    sa.Column('distancia_m', sa.Float(), nullable=True),
    sa.Column('fc_media', sa.Float(), nullable=True),
    sa.Column('pace_s_km', sa.Float(), nullable=True),
    sa.Column('zona', sa.String(length=20), nullable=True),
    sa.Column('equipamento', sa.String(length=40), nullable=True),
    sa.CheckConstraint("tipo IN ('volta', 'tiro', 'recuperacao')", name=op.f('ck_segmento_tipo')),
    sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_segmento_atividade_id_atividade'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_segmento')),
    sa.UniqueConstraint('atividade_id', 'ordem', name='uq_segmento_ordem')
    )
    op.create_index(op.f('ix_segmento_atividade_id'), 'segmento', ['atividade_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_segmento_atividade_id'), table_name='segmento')
    op.drop_table('segmento')
    op.drop_table('vinculo_professor_atleta')
    op.drop_index(op.f('ix_atividade_inicio'), table_name='atividade')
    op.drop_index(op.f('ix_atividade_atleta_id'), table_name='atividade')
    op.drop_table('atividade')
    op.drop_table('professor')
    op.drop_table('atleta')
    op.drop_table('assessoria')

