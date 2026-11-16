"""feedback_treino.clima_visto (#409, adendo 4 da ADR 0013)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-16 12:00:00.000000

Aditiva: uma coluna anulavel (SHA-256 do clima que o pacote viu). Linhas existentes ficam `NULL` = "nao se sabe o que o pacote
viu": o clima nao entra na comparacao delas, entao nenhuma vai para a fila de uma vez. No SQLite a coluna entra por
`batch_alter_table`. O `downgrade` remove a coluna.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0015'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.add_column(sa.Column('clima_visto', sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.drop_column('clima_visto')
