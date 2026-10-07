from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, conexao_usuario

_NAO_INFORMADO = object()

TIPOS_CONTA = {
    "conta_corrente",
    "conta_digital",
    "poupanca",
    "dinheiro",
    "investimento",
    "outro",
}


def _validar_nome(nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("O nome da conta não pode ser vazio.")


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_CONTA:
        raise ValueError(
            f"Tipo de conta inválido: '{tipo}'. Tipos aceitos: {sorted(TIPOS_CONTA)}."
        )


def criar_conta(
    nome: str,
    tipo: str,
    instituicao: str | None = None,
    saldo_inicial: Decimal = Decimal("0"),
    data_saldo_inicial: date | None = None,
) -> int:
    _validar_nome(nome)
    _validar_tipo(tipo)
    if not isinstance(saldo_inicial, Decimal):
        raise ValueError("saldo_inicial deve ser do tipo Decimal.")
    if data_saldo_inicial is not None and not isinstance(data_saldo_inicial, date):
        raise ValueError("data_saldo_inicial deve ser um objeto date.")

    try:
        with conexao_usuario() as conn:
            resultado = conn.execute(
                text(
                    """
                    INSERT INTO contas (nome, tipo, instituicao, saldo_inicial, data_saldo_inicial)
                    VALUES (:nome, :tipo, :instituicao, :saldo_inicial, :data_saldo_inicial)
                    RETURNING id
                    """
                ),
                {
                    "nome": nome,
                    "tipo": tipo,
                    "instituicao": instituicao,
                    "saldo_inicial": saldo_inicial,
                    "data_saldo_inicial": data_saldo_inicial,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar conta.") from exc


def obter_conta(id: int) -> dict | None:
    try:
        with conexao_usuario() as conn:
            linha = conn.execute(
                text("SELECT * FROM contas WHERE id = :id"), {"id": id}
            ).mappings().first()
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter conta.") from exc


def listar_contas(incluir_inativas: bool = False) -> list[dict]:
    if incluir_inativas:
        consulta = text("SELECT * FROM contas ORDER BY nome")
    else:
        consulta = text("SELECT * FROM contas WHERE ativa = true ORDER BY nome")

    try:
        with conexao_usuario() as conn:
            linhas = conn.execute(consulta).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar contas.") from exc


def atualizar_conta(
    id: int,
    nome: str | None = None,
    tipo: str | None = None,
    instituicao: str | None = None,
    saldo_inicial: Decimal | None = None,
    data_saldo_inicial=_NAO_INFORMADO,
    ativa: bool | None = None,
) -> None:
    campos: dict[str, object] = {}

    if nome is not None:
        _validar_nome(nome)
        campos["nome"] = nome
    if tipo is not None:
        _validar_tipo(tipo)
        campos["tipo"] = tipo
    if instituicao is not None:
        campos["instituicao"] = instituicao
    if saldo_inicial is not None:
        if not isinstance(saldo_inicial, Decimal):
            raise ValueError("saldo_inicial deve ser do tipo Decimal.")
        campos["saldo_inicial"] = saldo_inicial
    if data_saldo_inicial is not _NAO_INFORMADO:
        if data_saldo_inicial is not None and not isinstance(data_saldo_inicial, date):
            raise ValueError("data_saldo_inicial deve ser um objeto date.")
        campos["data_saldo_inicial"] = data_saldo_inicial
    if ativa is not None:
        campos["ativa"] = ativa

    if not campos:
        return

    atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
    campos["id"] = id

    try:
        with conexao_usuario() as conn:
            resultado = conn.execute(
                text(
                    f"UPDATE contas SET {atribuicoes}, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                campos,
            )
            if resultado.rowcount == 0:
                raise ValueError(f"Conta {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar conta.") from exc


def excluir_conta(id: int) -> None:
    try:
        with conexao_usuario() as conn:
            tem_transacoes = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM transacoes
                        WHERE conta_id = :id OR conta_destino_id = :id
                    )
                    """
                ),
                {"id": id},
            ).scalar_one()

            if tem_transacoes:
                resultado = conn.execute(
                    text(
                        "UPDATE contas SET ativa = false, atualizado_em = now() "
                        "WHERE id = :id"
                    ),
                    {"id": id},
                )
            else:
                resultado = conn.execute(
                    text("DELETE FROM contas WHERE id = :id"), {"id": id}
                )

            if resultado.rowcount == 0:
                raise ValueError(f"Conta {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir conta.") from exc
