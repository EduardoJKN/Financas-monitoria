"""corrige recursao infinita na politica de rls de categorias

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06

A política de RLS de `categorias` (migration 0005) validava, no WITH CHECK,
que `categoria_pai_id` apontasse para uma categoria do mesmo usuário usando
uma subconsulta contra a própria tabela `categorias`. O PostgreSQL não
suporta isso: uma política que referencia a própria tabela (self-reference)
faz com que a avaliação da política se torne recursiva, e o Postgres aborta
com "infinite recursion detected in policy for relation categorias" em
qualquer INSERT/UPDATE em categorias.

A correção padrão documentada para esse caso é mover a checagem para dentro
de uma função SECURITY DEFINER: dentro dela, o Postgres avalia o SELECT como
o owner da função (aqui, a role administrativa, que tem BYPASSRLS — ver
migration 0005), então a política de categorias não é reaplicada e não há
recursão. A função ainda assim só retorna true quando a categoria pai
realmente pertence ao usuário informado, então a checagem de segurança
continua correta e equivalente à intenção original.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_categoria_pai_valida(
            p_categoria_pai_id integer, p_usuario_id uuid
        ) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT p_categoria_pai_id IS NULL OR EXISTS (
                SELECT 1 FROM categorias
                WHERE id = p_categoria_pai_id AND usuario_id = p_usuario_id
            )
        $$;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION app_categoria_pai_valida(integer, uuid) TO app_runtime")

    op.execute("DROP POLICY IF EXISTS iso_categorias ON categorias")
    op.execute(
        """
        CREATE POLICY iso_categorias ON categorias
        USING (usuario_id = app_usuario_atual())
        WITH CHECK (
            usuario_id = app_usuario_atual()
            AND app_categoria_pai_valida(categoria_pai_id, app_usuario_atual())
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS iso_categorias ON categorias")
    op.execute(
        """
        CREATE POLICY iso_categorias ON categorias
        USING (usuario_id = app_usuario_atual())
        WITH CHECK (
            usuario_id = app_usuario_atual()
            AND (categoria_pai_id IS NULL OR categoria_pai_id IN (
                SELECT id FROM categorias WHERE usuario_id = app_usuario_atual()
            ))
        )
        """
    )
    op.execute("DROP FUNCTION IF EXISTS app_categoria_pai_valida(integer, uuid)")
