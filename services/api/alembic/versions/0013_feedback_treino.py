"""tabela feedback_treino (ADR 0013, item 2)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-10 20:00:00.000000

Aditiva: nao edita tabelas anteriores. O `downgrade` apaga a tabela e, com ela, os feedbacks (texto derivado do check-in,
dado de saude, sem copia). O `UNIQUE` de `checkin_id` ja indexa; nenhum indice a mais.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0013'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'feedback_treino',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checkin_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('motivo', sa.String(length=30), nullable=True),
        sa.Column('texto', sa.String(), nullable=True),
        sa.Column('versao_fatos', sa.String(length=20), nullable=False),
        sa.Column('versao_prompt', sa.String(length=40), nullable=False),
        sa.Column('versao_checagens', sa.String(length=40), nullable=False),
        sa.Column('provedor', sa.String(length=40), nullable=True),
        sa.Column('modelo', sa.String(length=80), nullable=True),
        sa.Column('tentativas', sa.Integer(), server_default='1', nullable=False),
        sa.Column('checkin_atualizado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tentado_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("estado IN ('pronto', 'sem_feedback')", name=op.f('ck_feedback_treino_estado')),
        sa.CheckConstraint(
            "motivo IS NULL OR motivo IN ('texto_reprovado', 'provedor_erro', 'provedor_tempo_limite', "
            "'provedor_nao_configurado', 'limite_de_chamadas')",
            name=op.f('ck_feedback_treino_motivo'),
        ),
        sa.CheckConstraint("texto IS NULL OR length(texto) BETWEEN 1 AND 700", name=op.f('ck_feedback_treino_texto_tamanho')),
        sa.CheckConstraint(
            "(estado = 'pronto' AND texto IS NOT NULL AND motivo IS NULL AND provedor IS NOT NULL AND modelo IS NOT NULL) OR "
            "(estado = 'sem_feedback' AND texto IS NULL AND motivo IS NOT NULL)",
            name=op.f('ck_feedback_treino_estado_campos'),
        ),
        sa.ForeignKeyConstraint(['checkin_id'], ['checkin_treino.id'], name=op.f('fk_feedback_treino_checkin_id_checkin_treino'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback_treino')),
        sa.UniqueConstraint('checkin_id', name=op.f('uq_feedback_treino_checkin_id')),
    )


def downgrade() -> None:
    op.drop_table('feedback_treino')
