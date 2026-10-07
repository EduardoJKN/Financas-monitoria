"""adiciona data_saldo_inicial para conciliacao de saldo

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06

saldo_inicial, até aqui, não tinha uma data de referência explícita: o
cálculo de saldo somava TODAS as movimentações da conta a saldo_inicial,
em qualquer data. Isso é inconsistente quando saldo_inicial já representa o
saldo bancário em um certo dia (ex.: ao cadastrar a conta, o usuário informa
"tinha R$ 1.000 em 01/09/2026") — movimentações anteriores a essa data já
estão implicitamente contempladas nesse valor e não deveriam ser somadas de
novo.

data_saldo_inicial é NULLABLE e aditiva: contas já existentes ficam sem
data de referência (comportamento de cálculo inalterado — todas as
movimentações continuam entrando na soma, exatamente como antes) e são
sinalizadas na interface como "precisa de conciliação". Nenhum dado
existente é alterado ou perdido.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contas", sa.Column("data_saldo_inicial", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("contas", "data_saldo_inicial")
