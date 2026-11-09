"""semana_padrao, semana_padrao_item e colunas de tipo em atividade (ADR 0011, item 1)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09 12:00:00.000000

Aditiva e reversivel; nada e preenchido. O `downgrade` apaga o que a semana-padrao derivou (tipo, origem, versao e
divergencia das linhas com origem `semana_padrao`): e reaplicavel.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPOS = "'leve', 'moderado', 'longo', 'intervalado', 'fartlek'"
_ORIGEM_ANTIGA = "tipo_origem IS NULL OR tipo_origem IN ('sugestao', 'professor', 'trainingpeaks')"
_ORIGEM_NOVA = "tipo_origem IS NULL OR tipo_origem IN ('sugestao', 'professor', 'trainingpeaks', 'semana_padrao')"


def upgrade() -> None:
    op.create_table(
        'semana_padrao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('vigente_desde', sa.Date(), nullable=False),
        sa.Column('definido_por', sa.String(length=20), nullable=False),
        sa.Column('definido_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("definido_por IN ('atleta', 'professor')", name=op.f('ck_semana_padrao_definido_por')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_semana_padrao_atleta_id_atleta')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_semana_padrao')),
        sa.UniqueConstraint('atleta_id', 'vigente_desde', name='uq_semana_padrao_vigencia'),
    )
    op.create_table(
        'semana_padrao_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semana_padrao_id', sa.Integer(), nullable=False),
        sa.Column('dia_semana', sa.Integer(), nullable=False),
        sa.Column('modalidade', sa.String(length=20), nullable=False),
        sa.Column('tipo_treino', sa.String(length=20), nullable=True),
        sa.CheckConstraint("dia_semana BETWEEN 1 AND 7", name=op.f('ck_semana_padrao_item_dia_semana')),
        sa.CheckConstraint("modalidade IN ('corrida', 'natacao', 'ciclismo')", name=op.f('ck_semana_padrao_item_modalidade')),
        sa.CheckConstraint(f"tipo_treino IS NULL OR tipo_treino IN ({_TIPOS})", name=op.f('ck_semana_padrao_item_tipo_treino')),
        sa.ForeignKeyConstraint(
            ['semana_padrao_id'], ['semana_padrao.id'],
            name=op.f('fk_semana_padrao_item_semana_padrao_id_semana_padrao'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_semana_padrao_item')),
        sa.UniqueConstraint('semana_padrao_id', 'dia_semana', 'modalidade', name='uq_semana_padrao_item_dia_modalidade'),
    )
    op.create_index(op.f('ix_semana_padrao_item_semana_padrao_id'), 'semana_padrao_item', ['semana_padrao_id'], unique=False)

    # batch: o SQLite nao altera CHECK com ALTER TABLE; no Postgres vira ALTER normal (drop + create da constraint).
    with op.batch_alter_table('atividade') as batch:
        batch.add_column(sa.Column('tipo_versao', sa.String(length=40), nullable=True))
        batch.add_column(sa.Column('tipo_divergencia', sa.String(length=20), nullable=True))
        batch.drop_constraint(op.f('ck_atividade_tipo_origem'), type_='check')
        batch.create_check_constraint(op.f('ck_atividade_tipo_origem'), _ORIGEM_NOVA)
        batch.create_check_constraint(
            op.f('ck_atividade_tipo_divergencia'), "tipo_divergencia IS NULL OR tipo_divergencia IN ('sem_esforco', 'tem_tiros')")
        batch.create_check_constraint(
            op.f('ck_atividade_tipo_divergencia_origem'), "tipo_divergencia IS NULL OR (tipo_origem IS NOT NULL AND tipo_origem = 'semana_padrao')")


def downgrade() -> None:
    # 1. o que a semana-padrao escreveu e derivado e se reaplica: zera antes de recriar o CHECK antigo
    op.execute(
        "UPDATE atividade SET tipo_treino = NULL, tipo_origem = NULL, tipo_versao = NULL, tipo_divergencia = NULL "
        "WHERE tipo_origem = 'semana_padrao'"
    )
    # 2. CHECKs da divergencia, 3. CHECK antigo de tipo_origem, 4. colunas
    with op.batch_alter_table('atividade') as batch:
        batch.drop_constraint(op.f('ck_atividade_tipo_divergencia_origem'), type_='check')
        batch.drop_constraint(op.f('ck_atividade_tipo_divergencia'), type_='check')
        batch.drop_constraint(op.f('ck_atividade_tipo_origem'), type_='check')
        batch.create_check_constraint(op.f('ck_atividade_tipo_origem'), _ORIGEM_ANTIGA)
        batch.drop_column('tipo_divergencia')
        batch.drop_column('tipo_versao')
    # 5. tabelas: itens primeiro
    op.drop_index(op.f('ix_semana_padrao_item_semana_padrao_id'), table_name='semana_padrao_item')
    op.drop_table('semana_padrao_item')
    op.drop_table('semana_padrao')
