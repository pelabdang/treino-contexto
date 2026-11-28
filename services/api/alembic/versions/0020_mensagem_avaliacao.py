"""mensagem.avaliacao e avaliada_em: 👍/👎 do atleta na resposta do chat (adendo 17 da ADR 0004)

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-28 18:00:00.000000

Aditiva: duas colunas anulaveis; nenhuma linha existente muda (todas ficam `NULL`).
- `avaliacao`: 1, -1 ou `NULL` (CHECK); so em mensagem `respondida` (CHECK). Sem texto livre.
- `avaliada_em`: quando; `NULL` se e so se `avaliacao` e `NULL` (CHECK).
No SQLite as colunas e os CHECKs entram por `batch_alter_table`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0020'
down_revision: str | None = '0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('mensagem') as batch:
        batch.add_column(sa.Column('avaliacao', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('avaliada_em', sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint(op.f('ck_mensagem_avaliacao'), 'avaliacao IS NULL OR avaliacao IN (-1, 1)')
        batch.create_check_constraint(op.f('ck_mensagem_avaliacao_e_data'), '(avaliacao IS NULL) = (avaliada_em IS NULL)')
        batch.create_check_constraint(op.f('ck_mensagem_avaliacao_so_respondida'), "avaliacao IS NULL OR estado = 'respondida'")


def downgrade() -> None:
    with op.batch_alter_table('mensagem') as batch:
        batch.drop_constraint(op.f('ck_mensagem_avaliacao_so_respondida'), type_='check')
        batch.drop_constraint(op.f('ck_mensagem_avaliacao_e_data'), type_='check')
        batch.drop_constraint(op.f('ck_mensagem_avaliacao'), type_='check')
        batch.drop_column('avaliada_em')
        batch.drop_column('avaliacao')
