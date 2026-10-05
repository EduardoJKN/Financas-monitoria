"""adiciona cartoes de credito

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    agora = sa.text("now()")

    op.create_table(
        "cartoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("instituicao", sa.String(length=120), nullable=True),
        sa.Column("limite", sa.Numeric(14, 2), nullable=False),
        sa.Column("dia_fechamento", sa.SmallInteger(), nullable=False),
        sa.Column("dia_vencimento", sa.SmallInteger(), nullable=False),
        sa.Column("conta_pagamento_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=agora
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=agora,
        ),
        sa.ForeignKeyConstraint(
            ["conta_pagamento_id"],
            ["contas.id"],
            name="fk_cartoes_conta_pagamento_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("limite >= 0", name="ck_cartoes_limite_nao_negativo"),
        sa.CheckConstraint(
            "dia_fechamento >= 1 AND dia_fechamento <= 31",
            name="ck_cartoes_dia_fechamento_valido",
        ),
        sa.CheckConstraint(
            "dia_vencimento >= 1 AND dia_vencimento <= 31",
            name="ck_cartoes_dia_vencimento_valido",
        ),
    )
    op.create_index(
        "ix_cartoes_conta_pagamento_id", "cartoes", ["conta_pagamento_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cartoes_conta_pagamento_id", table_name="cartoes")
    op.drop_table("cartoes")
