"""tabela recuperacao_dia e feedback_treino.recuperacao_importada_em (ADR 0014, item 1)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-12 18:00:00.000000

Aditiva: tabela nova e uma coluna anulavel em `feedback_treino` (no SQLite por `batch_alter_table`). O `downgrade`
remove a coluna e apaga a tabela (dado de saude derivado de uma fonte que se rebusca). O `UNIQUE` e o indice de `atleta_id`
bastam; nenhum indice a mais.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0014'
down_revision: str | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'recuperacao_dia',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atleta_id', sa.Integer(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('noite', sa.Date(), nullable=False),
        sa.Column('sono_s', sa.Integer(), nullable=True),
        sa.Column('vfc_ms', sa.Float(), nullable=True),
        sa.Column('fc_repouso_bpm', sa.Integer(), nullable=True),
        sa.Column('versao_leitura', sa.String(length=40), nullable=False),
        sa.Column('importado_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origem IN ('garmin_connect')", name=op.f('ck_recuperacao_dia_origem')),
        sa.CheckConstraint("sono_s IS NULL OR sono_s BETWEEN 1 AND 86400", name=op.f('ck_recuperacao_dia_sono_s')),
        sa.CheckConstraint("vfc_ms IS NULL OR (vfc_ms > 0 AND vfc_ms <= 500)", name=op.f('ck_recuperacao_dia_vfc_ms')),
        sa.CheckConstraint("fc_repouso_bpm IS NULL OR fc_repouso_bpm BETWEEN 20 AND 150",
                           name=op.f('ck_recuperacao_dia_fc_repouso_bpm')),
        sa.CheckConstraint("sono_s IS NOT NULL OR vfc_ms IS NOT NULL OR fc_repouso_bpm IS NOT NULL",
                           name=op.f('ck_recuperacao_dia_alguma_medida')),
        sa.ForeignKeyConstraint(['atleta_id'], ['atleta.id'], name=op.f('fk_recuperacao_dia_atleta_id_atleta'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recuperacao_dia')),
        sa.UniqueConstraint('atleta_id', 'origem', 'noite', name='uq_recuperacao_dia_chave'),
    )
    op.create_index(op.f('ix_recuperacao_dia_atleta_id'), 'recuperacao_dia', ['atleta_id'], unique=False)
    with op.batch_alter_table('feedback_treino') as batch:
        batch.add_column(sa.Column('recuperacao_importada_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.drop_column('recuperacao_importada_em')
    op.drop_index(op.f('ix_recuperacao_dia_atleta_id'), table_name='recuperacao_dia')
    op.drop_table('recuperacao_dia')
