"""tabela checkin_treino (ADR 0012, item 1)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-09 18:00:00.000000

Aditiva: nao edita tabelas anteriores. O `downgrade` apaga a tabela e, com ela, os check-ins (dado do atleta, sem copia).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'checkin_treino',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('atividade_id', sa.Integer(), nullable=False),
        sa.Column('pse', sa.Integer(), nullable=False),
        sa.Column('sensacao', sa.Integer(), nullable=False),
        sa.Column('nada_a_relatar', sa.Boolean(), nullable=False),
        sa.Column('dor', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('cansaco', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('sono_ruim', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('calor', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('trabalho_estresse', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('texto', sa.String(), nullable=True),
        sa.Column('versao', sa.String(length=20), nullable=False),
        sa.Column('registrado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("pse BETWEEN 0 AND 10", name=op.f('ck_checkin_treino_pse')),
        sa.CheckConstraint("sensacao BETWEEN 1 AND 5", name=op.f('ck_checkin_treino_sensacao')),
        sa.CheckConstraint("texto IS NULL OR length(texto) BETWEEN 1 AND 500", name=op.f('ck_checkin_treino_texto_tamanho')),
        sa.CheckConstraint(
            "(nada_a_relatar = TRUE AND dor = FALSE AND cansaco = FALSE AND sono_ruim = FALSE AND calor = FALSE "
            "AND trabalho_estresse = FALSE AND texto IS NULL) OR "
            "(nada_a_relatar = FALSE AND (dor = TRUE OR cansaco = TRUE OR sono_ruim = TRUE OR calor = TRUE "
            "OR trabalho_estresse = TRUE OR texto IS NOT NULL))",
            name=op.f('ck_checkin_treino_observacao_coerente'),
        ),
        sa.ForeignKeyConstraint(['atividade_id'], ['atividade.id'], name=op.f('fk_checkin_treino_atividade_id_atividade'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_checkin_treino')),
        sa.UniqueConstraint('atividade_id', name=op.f('uq_checkin_treino_atividade_id')),
    )


def downgrade() -> None:
    op.drop_table('checkin_treino')
