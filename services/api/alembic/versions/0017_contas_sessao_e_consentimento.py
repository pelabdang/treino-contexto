"""conta, sessao, tentativa_login, consentimento_evento e colunas do vinculo (#499, ADR 0016, item 1)

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-17 16:00:00.000000

Aditiva: quatro tabelas novas e duas colunas anulaveis no vinculo; nenhuma linha existente muda.
- `conta`: e-mail unico (minusculas), `senha_hash`, `atleta_id` OU `professor_id` (CHECK `um_papel`), cada um unico.
- `sessao`: so o hash SHA-256 do token; `ON DELETE CASCADE` com a conta.
- `tentativa_login`: hash do e-mail, quando e se deu certo (forca bruta). Sem IP.
- `consentimento_evento`: trilha so de acrescimo (aceito ou revogado, com a versao do termo).
- `vinculo_professor_atleta.termo_versao` e `.consentimento_revogado_em`: anulaveis.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0017'
down_revision: str | None = '0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'conta',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column('atleta_id', sa.Integer(), sa.ForeignKey('atleta.id'), nullable=True),
        sa.Column('professor_id', sa.Integer(), sa.ForeignKey('professor.id'), nullable=True),
        sa.Column('ativa', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('deve_trocar_senha', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('senha_trocada_em', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('email', name=op.f('uq_conta_email')),
        sa.UniqueConstraint('atleta_id', name=op.f('uq_conta_atleta_id')),
        sa.UniqueConstraint('professor_id', name=op.f('uq_conta_professor_id')),
        sa.CheckConstraint('(atleta_id IS NULL) <> (professor_id IS NULL)', name=op.f('ck_conta_um_papel')),
    )
    op.create_table(
        'sessao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('conta.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revogada_em', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('token_hash', name=op.f('uq_sessao_token_hash')),
    )
    op.create_table(
        'tentativa_login',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('ocorrida_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ok', sa.Boolean(), nullable=False),
    )
    op.create_index('ix_tentativa_login_email_hash', 'tentativa_login', ['email_hash'])
    op.create_table(
        'consentimento_evento',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('atleta_id', sa.Integer(), sa.ForeignKey('atleta.id'), nullable=False),
        sa.Column('professor_id', sa.Integer(), sa.ForeignKey('professor.id'), nullable=False),
        sa.Column('acao', sa.String(length=10), nullable=False),
        sa.Column('termo_versao', sa.String(length=40), nullable=False),
        sa.Column('ocorrida_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("acao IN ('aceito', 'revogado')", name=op.f('ck_consentimento_evento_acao')),
    )
    with op.batch_alter_table('vinculo_professor_atleta') as batch:
        batch.add_column(sa.Column('termo_versao', sa.String(length=40), nullable=True))
        batch.add_column(sa.Column('consentimento_revogado_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('vinculo_professor_atleta') as batch:
        batch.drop_column('consentimento_revogado_em')
        batch.drop_column('termo_versao')
    op.drop_table('consentimento_evento')
    op.drop_index('ix_tentativa_login_email_hash', table_name='tentativa_login')
    op.drop_table('tentativa_login')
    op.drop_table('sessao')
    op.drop_table('conta')
