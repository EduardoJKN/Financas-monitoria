"""Cartões de crédito (tabela cartoes).

Um cartão é modelado separadamente de uma conta bancária: ele tem limite,
dia de fechamento e dia de vencimento próprios, e suas compras não reduzem
o saldo bancário imediatamente (isso só acontece quando a fatura é paga —
veja src/faturas.py).
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, obter_engine

_NAO_INFORMADO = object()


def _validar_nome(nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("O nome do cartão não pode ser vazio.")


def _validar_limite(limite: Decimal) -> None:
    if not isinstance(limite, Decimal):
        raise ValueError("limite deve ser do tipo Decimal.")
    if limite < 0:
        raise ValueError("limite não pode ser negativo.")


def _validar_dia(dia: int, nome_campo: str) -> None:
    if not isinstance(dia, int) or isinstance(dia, bool) or dia < 1 or dia > 31:
        raise ValueError(f"{nome_campo} deve ser um inteiro entre 1 e 31.")


def _validar_conta_pagamento(conn, conta_pagamento_id: int) -> None:
    conta = (
        conn.execute(
            text("SELECT ativa FROM contas WHERE id = :id"), {"id": conta_pagamento_id}
        )
        .mappings()
        .first()
    )
    if conta is None:
        raise ValueError(f"Conta de pagamento {conta_pagamento_id} não encontrada.")


def criar_cartao(
    nome: str,
    limite: Decimal,
    dia_fechamento: int,
    dia_vencimento: int,
    instituicao: str | None = None,
    conta_pagamento_id: int | None = None,
) -> int:
    _validar_nome(nome)
    _validar_limite(limite)
    _validar_dia(dia_fechamento, "dia_fechamento")
    _validar_dia(dia_vencimento, "dia_vencimento")

    try:
        with obter_engine().begin() as conn:
            if conta_pagamento_id is not None:
                _validar_conta_pagamento(conn, conta_pagamento_id)

            resultado = conn.execute(
                text(
                    """
                    INSERT INTO cartoes (
                        nome, instituicao, limite, dia_fechamento, dia_vencimento,
                        conta_pagamento_id
                    ) VALUES (
                        :nome, :instituicao, :limite, :dia_fechamento, :dia_vencimento,
                        :conta_pagamento_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "nome": nome.strip(),
                    "instituicao": instituicao,
                    "limite": limite,
                    "dia_fechamento": dia_fechamento,
                    "dia_vencimento": dia_vencimento,
                    "conta_pagamento_id": conta_pagamento_id,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar cartão.") from exc


def obter_cartao(id: int) -> dict | None:
    try:
        with obter_engine().connect() as conn:
            linha = (
                conn.execute(text("SELECT * FROM cartoes WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter cartão.") from exc


def listar_cartoes(incluir_inativos: bool = False) -> list[dict]:
    if incluir_inativos:
        consulta = text("SELECT * FROM cartoes ORDER BY nome")
    else:
        consulta = text("SELECT * FROM cartoes WHERE ativo = true ORDER BY nome")

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(consulta).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar cartões.") from exc


def atualizar_cartao(
    id: int,
    nome: str | None = None,
    instituicao=_NAO_INFORMADO,
    limite: Decimal | None = None,
    dia_fechamento: int | None = None,
    dia_vencimento: int | None = None,
    conta_pagamento_id=_NAO_INFORMADO,
    ativo: bool | None = None,
) -> None:
    if nome is not None:
        _validar_nome(nome)
    if limite is not None:
        _validar_limite(limite)
    if dia_fechamento is not None:
        _validar_dia(dia_fechamento, "dia_fechamento")
    if dia_vencimento is not None:
        _validar_dia(dia_vencimento, "dia_vencimento")

    try:
        with obter_engine().begin() as conn:
            atual = (
                conn.execute(text("SELECT * FROM cartoes WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            if atual is None:
                raise ValueError(f"Cartão {id} não encontrado.")

            conta_pagamento_final = (
                conta_pagamento_id
                if conta_pagamento_id is not _NAO_INFORMADO
                else atual["conta_pagamento_id"]
            )
            if conta_pagamento_final is not None:
                _validar_conta_pagamento(conn, conta_pagamento_final)

            campos: dict[str, object] = {}
            if nome is not None:
                campos["nome"] = nome.strip()
            if instituicao is not _NAO_INFORMADO:
                campos["instituicao"] = instituicao
            if limite is not None:
                campos["limite"] = limite
            if dia_fechamento is not None:
                campos["dia_fechamento"] = dia_fechamento
            if dia_vencimento is not None:
                campos["dia_vencimento"] = dia_vencimento
            if conta_pagamento_id is not _NAO_INFORMADO:
                campos["conta_pagamento_id"] = conta_pagamento_id
            if ativo is not None:
                campos["ativo"] = ativo

            if not campos:
                return

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
            campos["id"] = id
            conn.execute(
                text(
                    f"UPDATE cartoes SET {atribuicoes}, atualizado_em = now() WHERE id = :id"
                ),
                campos,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar cartão.") from exc


def excluir_cartao(id: int) -> None:
    """Exclui o cartão. Se houver faturas ou transações vinculadas, desativa
    em vez de excluir, preservando o histórico."""
    try:
        with obter_engine().begin() as conn:
            tem_dependencias = conn.execute(
                text(
                    """
                    SELECT
                        EXISTS (SELECT 1 FROM transacoes WHERE cartao_id = :id)
                        OR EXISTS (SELECT 1 FROM faturas_cartao WHERE cartao_id = :id)
                    """
                ),
                {"id": id},
            ).scalar_one()

            if tem_dependencias:
                resultado = conn.execute(
                    text(
                        "UPDATE cartoes SET ativo = false, atualizado_em = now() "
                        "WHERE id = :id"
                    ),
                    {"id": id},
                )
            else:
                resultado = conn.execute(
                    text("DELETE FROM cartoes WHERE id = :id"), {"id": id}
                )

            if resultado.rowcount == 0:
                raise ValueError(f"Cartão {id} não encontrado.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir cartão.") from exc
