"""atividade.tipo_confirmado_por/_em e feedback_treino.tipo_visto (#423, ADR 0015, item 1)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-16 15:00:00.000000

Aditiva: tres colunas anulaveis, nenhuma linha existente muda (todas ficam `NULL`).
- `atividade.tipo_confirmado_por`: FK `professor.id`, `ON DELETE SET NULL`, constraint NOMEADA `fk_atividade_tipo_confirmado_por`
  (no SQLite o `downgrade` so remove a coluna com FK nomeada). Sem CHECK: `tipo_confirmado` verdadeiro com `_por` nulo e legal.
- `atividade.tipo_confirmado_em`: datetime com fuso, definido pela aplicacao (sem `server_default`).
- `feedback_treino.tipo_visto`: o tipo que o pacote de fatos viu; `NULL` = linha anterior (nao compara), como o `clima_visto`.
No SQLite as colunas entram por `batch_alter_table`. O `downgrade` remove a FK e as tres colunas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0016'
down_revision: str | None = '0015'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = 'fk_atividade_tipo_confirmado_por'


def upgrade() -> None:
    with op.batch_alter_table('atividade') as batch:
        batch.add_column(sa.Column('tipo_confirmado_por', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('tipo_confirmado_em', sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(_FK, 'professor', ['tipo_confirmado_por'], ['id'], ondelete='SET NULL')
    with op.batch_alter_table('feedback_treino') as batch:
        batch.add_column(sa.Column('tipo_visto', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('feedback_treino') as batch:
        batch.drop_column('tipo_visto')
    with op.batch_alter_table('atividade') as batch:
        batch.drop_constraint(_FK, type_='foreignkey')
        batch.drop_column('tipo_confirmado_em')
        batch.drop_column('tipo_confirmado_por')
