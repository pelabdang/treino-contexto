"""feedback_treino.transicao_visto (#510, pergunta C da Meta 12)

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-18 15:00:00.000000

Aditiva: uma coluna anulavel, nenhuma linha existente muda (todas ficam `NULL`).
- `feedback_treino.transicao_visto`: se o pacote de fatos viu a atividade como parte de um treino de transicao
  (`parte_de_transicao`). `NULL` = linha anterior (nao compara), como `clima_visto` e `tipo_visto`. Quando o atleta corrige ou desfaz o
  rotulo de transicao, o valor de hoje deixa de bater com este e o feedback fica `desatualizado` (e o worker o refaz).
No SQLite a coluna entra por `batch_alter_table`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.add_column(sa.Column('transicao_visto', sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.drop_column('transicao_visto')
