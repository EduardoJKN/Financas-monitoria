"""adiciona recorrencias e vinculo com transacoes

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    agora = sa.text("now()")

    op.create_table(
        "recorrencias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("conta_id", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("periodicidade", sa.String(length=20), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("proxima_data", sa.Date(), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            ["categoria_id"],
            ["categorias.id"],
            name="fk_recorrencias_categoria_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conta_id"],
            ["contas.id"],
            name="fk_recorrencias_conta_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("tipo IN ('receita', 'despesa')", name="ck_recorrencias_tipo"),
        sa.CheckConstraint("valor > 0", name="ck_recorrencias_valor_positivo"),
        sa.CheckConstraint(
            "periodicidade IN ('mensal', 'semanal', 'anual')",
            name="ck_recorrencias_periodicidade",
        ),
        sa.CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="ck_recorrencias_data_fim_apos_inicio",
        ),
    )
    op.create_index("ix_recorrencias_conta_id", "recorrencias", ["conta_id"])
    op.create_index("ix_recorrencias_categoria_id", "recorrencias", ["categoria_id"])
    op.create_index("ix_recorrencias_proxima_data", "recorrencias", ["proxima_data"])

    # Vínculo opcional entre uma transação gerada e a recorrência que a originou.
    # Usado para consultas/relatórios; a idempotência da geração depende do
    # avanço de recorrencias.proxima_data, não deste vínculo.
    op.add_column(
        "transacoes", sa.Column("recorrencia_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_transacoes_recorrencia_id",
        "transacoes",
        "recorrencias",
        ["recorrencia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_transacoes_recorrencia_id", "transacoes", ["recorrencia_id"]
    )

    op.drop_constraint("ck_transacoes_origem", "transacoes", type_="check")
    op.create_check_constraint(
        "ck_transacoes_origem",
        "transacoes",
        "origem IN ('manual', 'importacao', 'recorrencia')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transacoes_origem", "transacoes", type_="check")
    op.create_check_constraint(
        "ck_transacoes_origem", "transacoes", "origem IN ('manual', 'importacao')"
    )

    op.drop_index("ix_transacoes_recorrencia_id", table_name="transacoes")
    op.drop_constraint("fk_transacoes_recorrencia_id", "transacoes", type_="foreignkey")
    op.drop_column("transacoes", "recorrencia_id")

    op.drop_index("ix_recorrencias_proxima_data", table_name="recorrencias")
    op.drop_index("ix_recorrencias_categoria_id", table_name="recorrencias")
    op.drop_index("ix_recorrencias_conta_id", table_name="recorrencias")
    op.drop_table("recorrencias")
