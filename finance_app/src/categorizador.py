"""Regras de categorização automática (tabela regras_categorizacao)."""

import re

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, obter_engine

OPERADORES_REGRA = {"contem", "comeca_com", "igual"}

_ESPACOS_MULTIPLOS = re.compile(r"\s+")


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação: remove espaços extras e ignora caixa."""
    texto = (texto or "").strip()
    texto = _ESPACOS_MULTIPLOS.sub(" ", texto)
    return texto.casefold()


def _validar_texto_busca(texto_busca: str) -> None:
    if not texto_busca or not texto_busca.strip():
        raise ValueError("O texto de busca da regra não pode ser vazio.")


def _validar_operador(operador: str) -> None:
    if operador not in OPERADORES_REGRA:
        raise ValueError(
            f"Operador inválido: '{operador}'. Operadores aceitos: {sorted(OPERADORES_REGRA)}."
        )


def _validar_prioridade(prioridade: int) -> None:
    if not isinstance(prioridade, int) or isinstance(prioridade, bool):
        raise ValueError("prioridade deve ser um número inteiro.")


def _validar_categoria_ativa(conn: Connection, categoria_id: int) -> dict:
    categoria = (
        conn.execute(
            text("SELECT tipo, ativa FROM categorias WHERE id = :id"),
            {"id": categoria_id},
        )
        .mappings()
        .first()
    )
    if categoria is None:
        raise ValueError(f"Categoria {categoria_id} não encontrada.")
    if not categoria["ativa"]:
        raise ValueError(f"Categoria {categoria_id} está inativa.")
    return dict(categoria)


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def criar_regra(
    texto_busca: str,
    operador: str,
    categoria_id: int,
    prioridade: int = 0,
) -> int:
    _validar_texto_busca(texto_busca)
    _validar_operador(operador)
    _validar_prioridade(prioridade)

    try:
        with obter_engine().begin() as conn:
            _validar_categoria_ativa(conn, categoria_id)
            resultado = conn.execute(
                text(
                    """
                    INSERT INTO regras_categorizacao
                        (texto_busca, operador, categoria_id, prioridade)
                    VALUES (:texto_busca, :operador, :categoria_id, :prioridade)
                    RETURNING id
                    """
                ),
                {
                    "texto_busca": texto_busca.strip(),
                    "operador": operador,
                    "categoria_id": categoria_id,
                    "prioridade": prioridade,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar regra de categorização.") from exc


def obter_regra(id: int) -> dict | None:
    try:
        with obter_engine().connect() as conn:
            linha = (
                conn.execute(
                    text("SELECT * FROM regras_categorizacao WHERE id = :id"), {"id": id}
                )
                .mappings()
                .first()
            )
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter regra de categorização.") from exc


def listar_regras(
    categoria_id: int | None = None, incluir_inativas: bool = False
) -> list[dict]:
    condicoes = []
    parametros: dict[str, object] = {}

    if not incluir_inativas:
        condicoes.append("ativa = true")
    if categoria_id is not None:
        condicoes.append("categoria_id = :categoria_id")
        parametros["categoria_id"] = categoria_id

    clausula_where = f" WHERE {' AND '.join(condicoes)}" if condicoes else ""
    consulta = text(
        f"SELECT * FROM regras_categorizacao{clausula_where} "
        "ORDER BY prioridade DESC, id"
    )

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(consulta, parametros).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar regras de categorização.") from exc


def atualizar_regra(
    id: int,
    texto_busca: str | None = None,
    operador: str | None = None,
    categoria_id: int | None = None,
    prioridade: int | None = None,
    ativa: bool | None = None,
) -> None:
    if texto_busca is not None:
        _validar_texto_busca(texto_busca)
    if operador is not None:
        _validar_operador(operador)
    if prioridade is not None:
        _validar_prioridade(prioridade)

    try:
        with obter_engine().begin() as conn:
            atual = (
                conn.execute(
                    text("SELECT * FROM regras_categorizacao WHERE id = :id"), {"id": id}
                )
                .mappings()
                .first()
            )
            if atual is None:
                raise ValueError(f"Regra {id} não encontrada.")

            categoria_final = (
                categoria_id if categoria_id is not None else atual["categoria_id"]
            )
            _validar_categoria_ativa(conn, categoria_final)

            campos: dict[str, object] = {}
            if texto_busca is not None:
                campos["texto_busca"] = texto_busca.strip()
            if operador is not None:
                campos["operador"] = operador
            if categoria_id is not None:
                campos["categoria_id"] = categoria_id
            if prioridade is not None:
                campos["prioridade"] = prioridade
            if ativa is not None:
                campos["ativa"] = ativa

            if not campos:
                return

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
            campos["id"] = id
            conn.execute(
                text(
                    f"UPDATE regras_categorizacao SET {atribuicoes}, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                campos,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar regra de categorização.") from exc


def excluir_regra(id: int) -> None:
    try:
        with obter_engine().begin() as conn:
            resultado = conn.execute(
                text("DELETE FROM regras_categorizacao WHERE id = :id"), {"id": id}
            )
            if resultado.rowcount == 0:
                raise ValueError(f"Regra {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir regra de categorização.") from exc


# ---------------------------------------------------------------------
# Categorização automática
# ---------------------------------------------------------------------
def _regra_corresponde(operador: str, texto_regra: str, descricao: str) -> bool:
    if operador == "contem":
        return texto_regra in descricao
    if operador == "comeca_com":
        return descricao.startswith(texto_regra)
    if operador == "igual":
        return descricao == texto_regra
    return False


def categorizar_descricao(descricao: str, tipo: str | None = None) -> int | None:
    """Retorna o id da categoria sugerida para a descrição, ou None se nenhuma
    regra ativa corresponder. Não usa IA: apenas comparação textual simples.
    """
    descricao_normalizada = normalizar_texto(descricao)
    if not descricao_normalizada:
        return None

    condicoes = ["r.ativa = true", "c.ativa = true"]
    parametros: dict[str, object] = {}
    if tipo is not None:
        condicoes.append("(c.tipo = 'ambos' OR c.tipo = :tipo)")
        parametros["tipo"] = tipo
    clausula_where = " AND ".join(condicoes)

    try:
        with obter_engine().connect() as conn:
            linhas = (
                conn.execute(
                    text(
                        f"""
                        SELECT r.operador, r.texto_busca, r.categoria_id
                        FROM regras_categorizacao r
                        JOIN categorias c ON c.id = r.categoria_id
                        WHERE {clausula_where}
                        ORDER BY r.prioridade DESC, r.id
                        """
                    ),
                    parametros,
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao categorizar descrição.") from exc

    for regra in linhas:
        texto_regra = normalizar_texto(regra["texto_busca"])
        if _regra_corresponde(regra["operador"], texto_regra, descricao_normalizada):
            return regra["categoria_id"]
    return None
