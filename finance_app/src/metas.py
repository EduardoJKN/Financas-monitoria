"""Metas financeiras (tabela metas)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, conexao_usuario

_NAO_INFORMADO = object()


def _validar_nome(nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("O nome da meta não pode ser vazio.")


def _validar_valor_alvo(valor_alvo: Decimal) -> None:
    if not isinstance(valor_alvo, Decimal):
        raise ValueError("valor_alvo deve ser do tipo Decimal.")
    if valor_alvo <= 0:
        raise ValueError("valor_alvo deve ser maior que zero.")


def _validar_valor_atual(valor_atual: Decimal) -> None:
    if not isinstance(valor_atual, Decimal):
        raise ValueError("valor_atual deve ser do tipo Decimal.")
    if valor_atual < 0:
        raise ValueError("valor_atual não pode ser negativo.")


def _validar_data_inicio(data_inicio: date) -> None:
    if not isinstance(data_inicio, date):
        raise ValueError("data_inicio deve ser um objeto date.")


def _validar_datas(data_inicio: date, data_limite: date | None) -> None:
    if data_limite is not None and data_limite < data_inicio:
        raise ValueError("data_limite não pode ser anterior a data_inicio.")


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def criar_meta(
    nome: str,
    data_inicio: date,
    valor_alvo: Decimal,
    valor_atual: Decimal = Decimal("0"),
    descricao: str | None = None,
    data_limite: date | None = None,
) -> int:
    _validar_nome(nome)
    _validar_valor_alvo(valor_alvo)
    _validar_valor_atual(valor_atual)
    _validar_data_inicio(data_inicio)
    _validar_datas(data_inicio, data_limite)

    concluida = valor_atual >= valor_alvo

    try:
        with conexao_usuario() as conn:
            resultado = conn.execute(
                text(
                    """
                    INSERT INTO metas
                        (nome, descricao, valor_alvo, valor_atual, data_inicio,
                         data_limite, concluida)
                    VALUES
                        (:nome, :descricao, :valor_alvo, :valor_atual, :data_inicio,
                         :data_limite, :concluida)
                    RETURNING id
                    """
                ),
                {
                    "nome": nome.strip(),
                    "descricao": descricao,
                    "valor_alvo": valor_alvo,
                    "valor_atual": valor_atual,
                    "data_inicio": data_inicio,
                    "data_limite": data_limite,
                    "concluida": concluida,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar meta.") from exc


def obter_meta(id: int) -> dict | None:
    try:
        with conexao_usuario() as conn:
            linha = (
                conn.execute(text("SELECT * FROM metas WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter meta.") from exc


def listar_metas(apenas_em_andamento: bool = False) -> list[dict]:
    if apenas_em_andamento:
        consulta = text(
            "SELECT * FROM metas WHERE concluida = false "
            "ORDER BY data_limite NULLS LAST, nome"
        )
    else:
        consulta = text(
            "SELECT * FROM metas ORDER BY concluida, data_limite NULLS LAST, nome"
        )

    try:
        with conexao_usuario() as conn:
            linhas = conn.execute(consulta).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar metas.") from exc


def atualizar_meta(
    id: int,
    nome: str | None = None,
    descricao=_NAO_INFORMADO,
    valor_alvo: Decimal | None = None,
    valor_atual: Decimal | None = None,
    data_inicio: date | None = None,
    data_limite=_NAO_INFORMADO,
) -> None:
    if nome is not None:
        _validar_nome(nome)
    if valor_alvo is not None:
        _validar_valor_alvo(valor_alvo)
    if valor_atual is not None:
        _validar_valor_atual(valor_atual)
    if data_inicio is not None:
        _validar_data_inicio(data_inicio)

    try:
        with conexao_usuario() as conn:
            atual = (
                conn.execute(text("SELECT * FROM metas WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            if atual is None:
                raise ValueError(f"Meta {id} não encontrada.")

            estado_final = {
                "nome": nome.strip() if nome is not None else atual["nome"],
                "descricao": (
                    descricao if descricao is not _NAO_INFORMADO else atual["descricao"]
                ),
                "valor_alvo": valor_alvo if valor_alvo is not None else atual["valor_alvo"],
                "valor_atual": (
                    valor_atual if valor_atual is not None else atual["valor_atual"]
                ),
                "data_inicio": (
                    data_inicio if data_inicio is not None else atual["data_inicio"]
                ),
                "data_limite": (
                    data_limite if data_limite is not _NAO_INFORMADO else atual["data_limite"]
                ),
            }
            _validar_datas(estado_final["data_inicio"], estado_final["data_limite"])
            estado_final["concluida"] = (
                estado_final["valor_atual"] >= estado_final["valor_alvo"]
            )

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in estado_final)
            estado_final["id"] = id
            conn.execute(
                text(
                    f"UPDATE metas SET {atribuicoes}, atualizado_em = now() WHERE id = :id"
                ),
                estado_final,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar meta.") from exc


def excluir_meta(id: int) -> None:
    try:
        with conexao_usuario() as conn:
            resultado = conn.execute(text("DELETE FROM metas WHERE id = :id"), {"id": id})
            if resultado.rowcount == 0:
                raise ValueError(f"Meta {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir meta.") from exc


# ---------------------------------------------------------------------
# Progresso
# ---------------------------------------------------------------------
def calcular_progresso_meta(id: int) -> dict:
    meta = obter_meta(id)
    if meta is None:
        raise ValueError(f"Meta {id} não encontrada.")

    valor_atual: Decimal = meta["valor_atual"]
    valor_alvo: Decimal = meta["valor_alvo"]
    concluida = valor_atual >= valor_alvo
    valor_restante = valor_alvo - valor_atual
    if valor_restante < 0:
        valor_restante = Decimal("0")

    if valor_alvo > 0:
        percentual = (valor_atual / valor_alvo) * Decimal("100")
    else:
        percentual = Decimal("100") if concluida else Decimal("0")

    if percentual > Decimal("100"):
        percentual = Decimal("100")
    elif percentual < Decimal("0"):
        percentual = Decimal("0")

    return {
        "meta_id": id,
        "valor_atual": valor_atual,
        "valor_alvo": valor_alvo,
        "valor_restante": valor_restante,
        "percentual": percentual,
        "concluida": concluida,
    }
