"""Reivindicação de dados legados (criados antes do multiusuário).

Única parte da aplicação que usa a conexão administrativa (obter_engine,
DATABASE_URL) para tocar dados potencialmente "sem dono" — necessário porque
a política de RLS nunca deixa a role de execução (app_runtime) ver uma linha
com usuario_id NULL, nem para o próprio dono reivindicá-la. A operação é
estreita (só esta função), guardada por uma linha de controle única
(migracao_legado, id=1) e atômica: ou associa todas as tabelas de uma vez ou
nenhuma. Depois que alguém reivindica, ninguém mais pode reivindicar de novo.
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, obter_engine

# Mesma lista de tabelas user-scoped da migration 0005 (mantida aqui em vez
# de importada dela: migrations não são um módulo estável para importar em
# runtime).
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


def existe_dados_legado_nao_reivindicados() -> bool:
    """True se a reivindicação ainda está disponível (ninguém reivindicou
    ainda) E existir ao menos um registro antigo (usuario_id IS NULL) em
    alguma tabela user-scoped para reivindicar."""
    try:
        with obter_engine().connect() as conn:
            ja_reivindicado = conn.execute(
                text(
                    "SELECT reivindicado_por_usuario_id IS NOT NULL FROM migracao_legado WHERE id = 1"
                )
            ).scalar_one()
            if ja_reivindicado:
                return False

            for tabela in TABELAS_USUARIO:
                tem_linha_sem_dono = conn.execute(
                    text(f"SELECT EXISTS (SELECT 1 FROM {tabela} WHERE usuario_id IS NULL)")
                ).scalar_one()
                if tem_linha_sem_dono:
                    return True
            return False
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao verificar dados legados.") from exc


def reivindicar_dados_legado(usuario_id: str) -> bool:
    """Associa todos os registros sem proprietário (usuario_id IS NULL) ao
    usuario_id informado. Retorna True se associou algo nesta chamada, False
    se a reivindicação já havia sido feita por outra pessoa anteriormente
    (nunca sobrescreve uma reivindicação já existente).

    Atômica: a UPDATE de controle (migracao_legado) só afeta a linha quando
    ela ainda não tinha dono, e todas as atualizações acontecem na mesma
    transação — ou tudo é associado, ou nada é.
    """
    try:
        with obter_engine().begin() as conn:
            resultado = conn.execute(
                text(
                    "UPDATE migracao_legado SET reivindicado_por_usuario_id = :uid, "
                    "reivindicado_em = now() WHERE id = 1 AND reivindicado_por_usuario_id IS NULL"
                ),
                {"uid": usuario_id},
            )
            if resultado.rowcount == 0:
                # já havia sido reivindicado por alguém antes desta chamada
                return False

            for tabela in TABELAS_USUARIO:
                conn.execute(
                    text(f"UPDATE {tabela} SET usuario_id = :uid WHERE usuario_id IS NULL"),
                    {"uid": usuario_id},
                )
            return True
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao reivindicar dados legados.") from exc


def obter_status_migracao_legado() -> dict | None:
    try:
        with obter_engine().connect() as conn:
            linha = conn.execute(
                text(
                    "SELECT reivindicado_por_usuario_id, reivindicado_em "
                    "FROM migracao_legado WHERE id = 1"
                )
            ).mappings().first()
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter status da migração de dados legados.") from exc
