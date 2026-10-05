"""adiciona faturas_cartao, pagamentos_fatura e suporte a compra no cartao

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-05

Esta migration torna transacoes.conta_id opcional e substitui a constraint
de forma de pagamento para permitir que uma despesa seja paga por conta OU
por cartão de crédito (nunca os dois, nunca nenhum). Nenhuma coluna é
removida e nenhum dado existente é apagado: todas as linhas atuais já têm
conta_id preenchido e cartao_id/fatura_id nulos, o que satisfaz a nova
constraint automaticamente.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_CHECK_FORMA_PAGAMENTO = (
    "(tipo = 'receita' AND conta_id IS NOT NULL AND cartao_id IS NULL "
    "   AND conta_destino_id IS NULL)"
    " OR (tipo = 'despesa' AND conta_id IS NOT NULL AND cartao_id IS NULL "
    "   AND conta_destino_id IS NULL)"
    " OR (tipo = 'despesa' AND conta_id IS NULL AND cartao_id IS NOT NULL "
    "   AND conta_destino_id IS NULL)"
    " OR (tipo = 'transferencia' AND conta_id IS NOT NULL "
    "   AND conta_destino_id IS NOT NULL AND conta_destino_id <> conta_id "
    "   AND cartao_id IS NULL)"
)


def upgrade() -> None:
    agora = sa.text("now()")

    # ---------------------------------------------------------------
    # faturas_cartao
    # ---------------------------------------------------------------
    op.create_table(
        "faturas_cartao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cartao_id", sa.Integer(), nullable=False),
        sa.Column("mes_referencia", sa.Date(), nullable=False),
        sa.Column("data_fechamento", sa.Date(), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="aberta"
        ),
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
            ["cartao_id"], ["cartoes.id"], name="fk_faturas_cartao_cartao_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('aberta', 'fechada', 'paga', 'parcial')",
            name="ck_faturas_cartao_status",
        ),
        sa.UniqueConstraint(
            "cartao_id", "mes_referencia", name="uq_faturas_cartao_cartao_mes"
        ),
    )
    op.create_index("ix_faturas_cartao_cartao_id", "faturas_cartao", ["cartao_id"])
    op.create_index(
        "ix_faturas_cartao_mes_referencia", "faturas_cartao", ["mes_referencia"]
    )

    # ---------------------------------------------------------------
    # pagamentos_fatura
    # ---------------------------------------------------------------
    op.create_table(
        "pagamentos_fatura",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fatura_id", sa.Integer(), nullable=False),
        sa.Column("conta_id", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=agora
        ),
        sa.ForeignKeyConstraint(
            ["fatura_id"], ["faturas_cartao.id"],
            name="fk_pagamentos_fatura_fatura_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conta_id"], ["contas.id"],
            name="fk_pagamentos_fatura_conta_id", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("valor > 0", name="ck_pagamentos_fatura_valor_positivo"),
    )
    op.create_index(
        "ix_pagamentos_fatura_fatura_id", "pagamentos_fatura", ["fatura_id"]
    )
    op.create_index(
        "ix_pagamentos_fatura_conta_id", "pagamentos_fatura", ["conta_id"]
    )

    # ---------------------------------------------------------------
    # transacoes: cartao_id, fatura_id, conta_id opcional, nova constraint
    # ---------------------------------------------------------------
    op.add_column("transacoes", sa.Column("cartao_id", sa.Integer(), nullable=True))
    op.add_column("transacoes", sa.Column("fatura_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_transacoes_cartao_id", "transacoes", "cartoes",
        ["cartao_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transacoes_fatura_id", "transacoes", "faturas_cartao",
        ["fatura_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_transacoes_cartao_id", "transacoes", ["cartao_id"])
    op.create_index("ix_transacoes_fatura_id", "transacoes", ["fatura_id"])

    op.alter_column("transacoes", "conta_id", existing_type=sa.Integer(), nullable=True)

    op.drop_constraint(
        "ck_transacoes_transferencia_contas", "transacoes", type_="check"
    )
    op.create_check_constraint(
        "ck_transacoes_forma_pagamento", "transacoes", _CHECK_FORMA_PAGAMENTO
    )


def downgrade() -> None:
    op.drop_constraint("ck_transacoes_forma_pagamento", "transacoes", type_="check")
    op.create_check_constraint(
        "ck_transacoes_transferencia_contas",
        "transacoes",
        "(tipo IN ('receita', 'despesa') AND conta_destino_id IS NULL) OR "
        "(tipo = 'transferencia' AND conta_destino_id IS NOT NULL "
        "AND conta_destino_id <> conta_id)",
    )
    op.alter_column("transacoes", "conta_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index("ix_transacoes_fatura_id", table_name="transacoes")
    op.drop_index("ix_transacoes_cartao_id", table_name="transacoes")
    op.drop_constraint("fk_transacoes_fatura_id", "transacoes", type_="foreignkey")
    op.drop_constraint("fk_transacoes_cartao_id", "transacoes", type_="foreignkey")
    op.drop_column("transacoes", "fatura_id")
    op.drop_column("transacoes", "cartao_id")

    op.drop_index("ix_pagamentos_fatura_conta_id", table_name="pagamentos_fatura")
    op.drop_index("ix_pagamentos_fatura_fatura_id", table_name="pagamentos_fatura")
    op.drop_table("pagamentos_fatura")

    op.drop_index("ix_faturas_cartao_mes_referencia", table_name="faturas_cartao")
    op.drop_index("ix_faturas_cartao_cartao_id", table_name="faturas_cartao")
    op.drop_table("faturas_cartao")
