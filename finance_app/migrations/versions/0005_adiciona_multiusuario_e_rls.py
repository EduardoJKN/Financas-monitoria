"""adiciona multiusuario (usuario_id) e isolamento real via RLS

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06

DECISÃO DE ARQUITETURA (ver também README.md):

A aplicação conecta ao Postgres com a role `postgres` do Supabase, que tem
BYPASSRLS=true e é owner de todas as tabelas (confirmado via
`SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user`). Isso
significa que simplesmente habilitar RLS não protegeria nada: essa role
ignora RLS por padrão, com ou sem política criada.

Por isso esta migration cria uma role nova, `app_runtime`, SEM BYPASSRLS e
SEM ser owner de nenhuma tabela, com apenas os GRANTs mínimos necessários
(SELECT/INSERT/UPDATE/DELETE nas tabelas user-scoped + USAGE nas sequences).
É essa role — não `postgres` — que a aplicação usa em tempo de execução
(APP_DATABASE_URL, lido por src/banco_de_dados.py:obter_engine_app()). A
migration continua rodando com a role administrativa (DATABASE_URL),
que precisa de privilégio de DDL.

O contexto do usuário autenticado é propagado por `set_config('app.usuario_id',
<uuid>, true)` no início de cada transação (ver conexao_usuario() em
src/banco_de_dados.py) — não por auth.uid()/JWT do PostgREST, já que a
aplicação não passa pelo PostgREST, conecta direto via SQLAlchemy/psycopg2.
A função `app_usuario_atual()` lê essa GUC e é usada em todas as políticas.

Cada política tem USING (visibilidade/leitura) e WITH CHECK (escrita). Para
tabelas com colunas de FK para outras tabelas user-scoped (ex.:
transacoes.conta_id), o WITH CHECK também exige que o registro referenciado
pertença ao mesmo usuário — isso é necessário porque checagens de
integridade referencial (FK) no Postgres ignoram RLS por padrão, então sem
essa checagem extra um usuário mal-intencionado poderia criar uma transação
apontando para o conta_id de outro usuário (usando um ID conhecido) mesmo
sem conseguir ler os dados dessa conta.

usuario_id é NULLABLE de propósito: as tabelas já têm dados reais (dados
pessoais do primeiro usuário, criados antes de existir multiusuário). Uma
linha com usuario_id NULL nunca é visível pela política de RLS (NULL =
qualquer coisa nunca é verdadeiro), então dados antigos ficam automaticamente
invisíveis/protegidos até serem explicitamente reivindicados pelo fluxo de
migração de dados legados (ver src/migracao_legado.py e tabela
migracao_legado criada abaixo). Novos registros sempre recebem usuario_id
automaticamente via DEFAULT (lido da mesma GUC), então nenhuma linha nova
jamais é criada sem proprietário enquanto a aplicação estiver em uso normal.

Nenhuma linha existente é apagada, alterada ou perde dados nesta migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Tabelas user-scoped e suas colunas de FK que também precisam pertencer
# ao mesmo usuário (validado no WITH CHECK). None = sem FK além da PK.
_TABELAS_SEM_FK = ("contas", "metas")

_CHECK_EXTRA = {
    "categorias": (
        "(categoria_pai_id IS NULL OR categoria_pai_id IN "
        "(SELECT id FROM categorias WHERE usuario_id = app_usuario_atual()))"
    ),
    "regras_categorizacao": (
        "categoria_id IN (SELECT id FROM categorias WHERE usuario_id = app_usuario_atual())"
    ),
    "recorrencias": (
        "conta_id IN (SELECT id FROM contas WHERE usuario_id = app_usuario_atual()) AND "
        "(categoria_id IS NULL OR categoria_id IN "
        "(SELECT id FROM categorias WHERE usuario_id = app_usuario_atual()))"
    ),
    "cartoes": (
        "(conta_pagamento_id IS NULL OR conta_pagamento_id IN "
        "(SELECT id FROM contas WHERE usuario_id = app_usuario_atual()))"
    ),
    "faturas_cartao": (
        "cartao_id IN (SELECT id FROM cartoes WHERE usuario_id = app_usuario_atual())"
    ),
    "pagamentos_fatura": (
        "fatura_id IN (SELECT id FROM faturas_cartao WHERE usuario_id = app_usuario_atual()) AND "
        "conta_id IN (SELECT id FROM contas WHERE usuario_id = app_usuario_atual())"
    ),
    "transacoes": (
        "(categoria_id IS NULL OR categoria_id IN "
        "(SELECT id FROM categorias WHERE usuario_id = app_usuario_atual())) AND "
        "(conta_id IS NULL OR conta_id IN "
        "(SELECT id FROM contas WHERE usuario_id = app_usuario_atual())) AND "
        "(conta_destino_id IS NULL OR conta_destino_id IN "
        "(SELECT id FROM contas WHERE usuario_id = app_usuario_atual())) AND "
        "(cartao_id IS NULL OR cartao_id IN "
        "(SELECT id FROM cartoes WHERE usuario_id = app_usuario_atual())) AND "
        "(fatura_id IS NULL OR fatura_id IN "
        "(SELECT id FROM faturas_cartao WHERE usuario_id = app_usuario_atual())) AND "
        "(recorrencia_id IS NULL OR recorrencia_id IN "
        "(SELECT id FROM recorrencias WHERE usuario_id = app_usuario_atual()))"
    ),
}

TABELAS_USUARIO = (
    "contas",
    "categorias",
    "transacoes",
    "regras_categorizacao",
    "metas",
    "recorrencias",
    "cartoes",
    "faturas_cartao",
    "pagamentos_fatura",
)


def upgrade() -> None:
    bind = op.get_bind()
    nome_banco = bind.engine.url.database

    # -----------------------------------------------------------------
    # 1) role de execução da aplicação, sem BYPASSRLS e sem ser owner
    # -----------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime LOGIN
                    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
            END IF;
        END
        $$;
        """
    )
    op.execute(f'GRANT CONNECT ON DATABASE "{nome_banco}" TO app_runtime')
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")

    # -----------------------------------------------------------------
    # 2) função auxiliar usada por todas as políticas de RLS
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_usuario_atual() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$
            SELECT current_setting('app.usuario_id', true)::uuid
        $$;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION app_usuario_atual() TO app_runtime")

    # -----------------------------------------------------------------
    # 3) usuario_id (nullable) em cada tabela user-scoped + índice
    # -----------------------------------------------------------------
    for tabela in TABELAS_USUARIO:
        op.add_column(tabela, sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.execute(
            f"ALTER TABLE {tabela} ALTER COLUMN usuario_id "
            "SET DEFAULT app_usuario_atual()"
        )
        op.create_index(f"ix_{tabela}_usuario_id", tabela, ["usuario_id"])
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabela} TO app_runtime")

    # -----------------------------------------------------------------
    # 4) RLS: habilita, força (mesmo para o owner) e cria as políticas
    # -----------------------------------------------------------------
    for tabela in TABELAS_USUARIO:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")

        checagem_extra = _CHECK_EXTRA.get(tabela)
        check_clause = "usuario_id = app_usuario_atual()"
        if checagem_extra:
            check_clause = f"{check_clause} AND {checagem_extra}"

        op.execute(
            f"""
            CREATE POLICY iso_{tabela} ON {tabela}
            USING (usuario_id = app_usuario_atual())
            WITH CHECK ({check_clause})
            """
        )

    # -----------------------------------------------------------------
    # 5) migração/claim de dados legados: linha única de controle
    # -----------------------------------------------------------------
    op.create_table(
        "migracao_legado",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("reivindicado_por_usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reivindicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_migracao_legado_linha_unica"),
    )
    op.execute(
        "INSERT INTO migracao_legado (id, reivindicado_por_usuario_id, reivindicado_em) "
        "VALUES (1, NULL, NULL)"
    )
    # migracao_legado NÃO é concedida a app_runtime de propósito: é uma
    # tabela de controle administrativo, não dado de usuário, e só é
    # acessada pela role administrativa através de src/migracao_legado.py.


def downgrade() -> None:
    op.drop_table("migracao_legado")

    for tabela in TABELAS_USUARIO:
        op.execute(f"DROP POLICY IF EXISTS iso_{tabela} ON {tabela}")
        op.execute(f"ALTER TABLE {tabela} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON {tabela} FROM app_runtime")
        op.drop_index(f"ix_{tabela}_usuario_id", table_name=tabela)
        op.drop_column(tabela, "usuario_id")

    op.execute("DROP FUNCTION IF EXISTS app_usuario_atual()")
    op.execute("REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_runtime")
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_runtime")
    bind = op.get_bind()
    nome_banco = bind.engine.url.database
    op.execute(f'REVOKE CONNECT ON DATABASE "{nome_banco}" FROM app_runtime')
    op.execute("DROP ROLE IF EXISTS app_runtime")
