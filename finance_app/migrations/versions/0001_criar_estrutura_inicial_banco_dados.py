"""cria estrutura inicial do banco de dados

Revision ID: 0001
Revises:
Create Date: 2026-09-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas_existentes = set(inspector.get_table_names(schema="public"))
    tabelas_da_migration = {
        "contas",
        "categorias",
        "transacoes",
        "regras_categorizacao",
        "metas",
    }
    conflito = tabelas_da_migration & tabelas_existentes
    if conflito:
        raise RuntimeError(
            "Conflito: as tabelas a seguir já existem no banco e não serão "
            f"recriadas para evitar perda de dados: {sorted(conflito)}"
        )

    agora = sa.text("now()")

    # ---------------------------------------------------------------
    # contas
    # ---------------------------------------------------------------
    op.create_table(
        "contas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("instituicao", sa.String(length=120), nullable=True),
        sa.Column(
            "saldo_inicial", sa.Numeric(14, 2), nullable=False, server_default="0"
        ),
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
        sa.CheckConstraint(
            "tipo IN ('conta_corrente', 'conta_digital', 'poupanca', 'dinheiro', "
            "'investimento', 'outro')",
            name="ck_contas_tipo",
        ),
    )

    # ---------------------------------------------------------------
    # categorias
    # ---------------------------------------------------------------
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("categoria_pai_id", sa.Integer(), nullable=True),
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
            ["categoria_pai_id"],
            ["categorias.id"],
            name="fk_categorias_categoria_pai_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "tipo IN ('receita', 'despesa', 'ambos')", name="ck_categorias_tipo"
        ),
    )
    op.create_index(
        "ix_categorias_categoria_pai_id", "categorias", ["categoria_pai_id"]
    )

    # ---------------------------------------------------------------
    # transacoes
    # ---------------------------------------------------------------
    op.create_table(
        "transacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("data_transacao", sa.Date(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("conta_id", sa.Integer(), nullable=False),
        sa.Column("conta_destino_id", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column(
            "origem", sa.String(length=20), nullable=False, server_default="manual"
        ),
        sa.Column("grupo_parcelamento", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("numero_parcela", sa.SmallInteger(), nullable=True),
        sa.Column("total_parcelas", sa.SmallInteger(), nullable=True),
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
            name="fk_transacoes_categoria_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conta_id"],
            ["contas.id"],
            name="fk_transacoes_conta_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conta_destino_id"],
            ["contas.id"],
            name="fk_transacoes_conta_destino_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "tipo IN ('receita', 'despesa', 'transferencia')",
            name="ck_transacoes_tipo",
        ),
        sa.CheckConstraint("valor > 0", name="ck_transacoes_valor_positivo"),
        sa.CheckConstraint(
            "origem IN ('manual', 'importacao')", name="ck_transacoes_origem"
        ),
        sa.CheckConstraint(
            "(tipo IN ('receita', 'despesa') AND conta_destino_id IS NULL) OR "
            "(tipo = 'transferencia' AND conta_destino_id IS NOT NULL "
            "AND conta_destino_id <> conta_id)",
            name="ck_transacoes_transferencia_contas",
        ),
        sa.CheckConstraint(
            "(numero_parcela IS NULL AND total_parcelas IS NULL) OR "
            "(numero_parcela IS NOT NULL AND total_parcelas IS NOT NULL "
            "AND numero_parcela >= 1 AND numero_parcela <= total_parcelas)",
            name="ck_transacoes_parcelas_coerentes",
        ),
    )
    op.create_index("ix_transacoes_data_transacao", "transacoes", ["data_transacao"])
    op.create_index("ix_transacoes_tipo", "transacoes", ["tipo"])
    op.create_index("ix_transacoes_categoria_id", "transacoes", ["categoria_id"])
    op.create_index("ix_transacoes_conta_id", "transacoes", ["conta_id"])
    op.create_index(
        "ix_transacoes_conta_destino_id", "transacoes", ["conta_destino_id"]
    )
    op.create_index(
        "ix_transacoes_grupo_parcelamento", "transacoes", ["grupo_parcelamento"]
    )

    # ---------------------------------------------------------------
    # regras_categorizacao
    # ---------------------------------------------------------------
    op.create_table(
        "regras_categorizacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("texto_busca", sa.String(length=255), nullable=False),
        sa.Column("operador", sa.String(length=20), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column(
            "prioridade", sa.Integer(), nullable=False, server_default="0"
        ),
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
            name="fk_regras_categorizacao_categoria_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "operador IN ('contem', 'comeca_com', 'igual')",
            name="ck_regras_categorizacao_operador",
        ),
    )
    op.create_index(
        "ix_regras_categorizacao_categoria_id", "regras_categorizacao", ["categoria_id"]
    )
    op.create_index(
        "ix_regras_categorizacao_prioridade", "regras_categorizacao", ["prioridade"]
    )

    # ---------------------------------------------------------------
    # metas
    # ---------------------------------------------------------------
    op.create_table(
        "metas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor_alvo", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "valor_atual", sa.Numeric(14, 2), nullable=False, server_default="0"
        ),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_limite", sa.Date(), nullable=True),
        sa.Column(
            "concluida", sa.Boolean(), nullable=False, server_default=sa.false()
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
        sa.CheckConstraint("valor_alvo > 0", name="ck_metas_valor_alvo_positivo"),
        sa.CheckConstraint("valor_atual >= 0", name="ck_metas_valor_atual_nao_negativo"),
        sa.CheckConstraint(
            "data_limite IS NULL OR data_limite >= data_inicio",
            name="ck_metas_data_limite_apos_inicio",
        ),
    )


def downgrade() -> None:
    op.drop_table("metas")
    op.drop_index("ix_regras_categorizacao_prioridade", table_name="regras_categorizacao")
    op.drop_index(
        "ix_regras_categorizacao_categoria_id", table_name="regras_categorizacao"
    )
    op.drop_table("regras_categorizacao")
    op.drop_index("ix_transacoes_grupo_parcelamento", table_name="transacoes")
    op.drop_index("ix_transacoes_conta_destino_id", table_name="transacoes")
    op.drop_index("ix_transacoes_conta_id", table_name="transacoes")
    op.drop_index("ix_transacoes_categoria_id", table_name="transacoes")
    op.drop_index("ix_transacoes_tipo", table_name="transacoes")
    op.drop_index("ix_transacoes_data_transacao", table_name="transacoes")
    op.drop_table("transacoes")
    op.drop_index("ix_categorias_categoria_pai_id", table_name="categorias")
    op.drop_table("categorias")
    op.drop_table("contas")
