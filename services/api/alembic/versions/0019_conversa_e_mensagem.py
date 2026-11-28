"""conversa e mensagem do chat do atleta (#597, ADR 0017, item 7)

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-28 12:00:00.000000

Aditiva: duas tabelas novas; nenhuma linha existente muda.
- `conversa`: `atleta_id` e `dono_conta_id` com `ON DELETE CASCADE`; `dono_papel` (`atleta` na Meta 14, `professor` na 16).
- `mensagem`: uma linha por pergunta e resposta; `chamadas_ferramenta` em JSON (JSONB no Postgres); `UNIQUE (conversa_id, ordem)`.
  Reprovada e erro gravam so o `motivo`, nunca o texto (CHECKs).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0019'
down_revision: str | None = '0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'conversa',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('atleta_id', sa.Integer(), sa.ForeignKey('atleta.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dono_papel', sa.String(length=10), nullable=False, server_default='atleta'),
        sa.Column('dono_conta_id', sa.Integer(), sa.ForeignKey('conta.id', ondelete='CASCADE'), nullable=False),
        sa.Column('titulo', sa.String(length=80), nullable=False),
        sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('atualizada_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("dono_papel IN ('atleta', 'professor')", name=op.f('ck_conversa_dono_papel')),
    )
    op.create_index('ix_conversa_atleta_id', 'conversa', ['atleta_id'])
    op.create_index('ix_conversa_dono_conta_id', 'conversa', ['dono_conta_id'])
    op.create_table(
        'mensagem',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conversa_id', sa.Integer(), sa.ForeignKey('conversa.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('pergunta', sa.String(length=1000), nullable=False),
        sa.Column('chamadas_ferramenta', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('resposta', sa.String(length=900), nullable=True),
        sa.Column('estado', sa.String(length=12), nullable=False),
        sa.Column('motivo', sa.String(length=40), nullable=True),
        sa.Column('versao_checagens', sa.String(length=40), nullable=False),
        sa.Column('versao_prompt', sa.String(length=40), nullable=False),
        sa.Column('provedor', sa.String(length=40), nullable=True),
        sa.Column('modelo', sa.String(length=80), nullable=True),
        sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('conversa_id', 'ordem', name=op.f('uq_mensagem_ordem')),
        sa.CheckConstraint("estado IN ('respondida', 'recusada', 'reprovada', 'erro')", name=op.f('ck_mensagem_estado')),
        sa.CheckConstraint("(estado = 'respondida') = (resposta IS NOT NULL AND motivo IS NULL)",
                           name=op.f('ck_mensagem_resposta_e_estado')),
        sa.CheckConstraint("estado <> 'recusada' OR resposta IS NOT NULL", name=op.f('ck_mensagem_recusada_com_texto')),
        sa.CheckConstraint("estado NOT IN ('reprovada', 'erro') OR (resposta IS NULL AND motivo IS NOT NULL)",
                           name=op.f('ck_mensagem_sem_texto_reprovado')),
    )
    op.create_index('ix_mensagem_conversa_id', 'mensagem', ['conversa_id'])


def downgrade() -> None:
    op.drop_index('ix_mensagem_conversa_id', table_name='mensagem')
    op.drop_table('mensagem')
    op.drop_index('ix_conversa_dono_conta_id', table_name='conversa')
    op.drop_index('ix_conversa_atleta_id', table_name='conversa')
    op.drop_table('conversa')
