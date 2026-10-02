from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, obter_engine

TIPOS_CATEGORIA = {"receita", "despesa", "ambos"}

_NAO_INFORMADO = object()


def _validar_nome(nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("O nome da categoria não pode ser vazio.")


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_CATEGORIA:
        raise ValueError(
            f"Tipo de categoria inválido: '{tipo}'. Tipos aceitos: {sorted(TIPOS_CATEGORIA)}."
        )


def _tipos_compativeis(tipo_pai: str, tipo_filha: str) -> bool:
    return tipo_pai == "ambos" or tipo_pai == tipo_filha


def _validar_pai(
    conn: Connection, categoria_pai_id: int, tipo_filha: str, id_atual: int | None
) -> None:
    if categoria_pai_id == id_atual:
        raise ValueError("Uma categoria não pode ser pai dela mesma.")

    pai = conn.execute(
        text("SELECT tipo, ativa FROM categorias WHERE id = :id"),
        {"id": categoria_pai_id},
    ).mappings().first()

    if pai is None:
        raise ValueError(f"Categoria pai {categoria_pai_id} não encontrada.")
    if not pai["ativa"]:
        raise ValueError(f"Categoria pai {categoria_pai_id} está inativa.")
    if not _tipos_compativeis(pai["tipo"], tipo_filha):
        raise ValueError(
            f"Tipo da categoria filha ('{tipo_filha}') incompatível com o tipo "
            f"da categoria pai ('{pai['tipo']}')."
        )


def criar_categoria(
    nome: str,
    tipo: str,
    categoria_pai_id: int | None = None,
) -> int:
    _validar_nome(nome)
    _validar_tipo(tipo)

    try:
        with obter_engine().begin() as conn:
            if categoria_pai_id is not None:
                _validar_pai(conn, categoria_pai_id, tipo, id_atual=None)

            resultado = conn.execute(
                text(
                    """
                    INSERT INTO categorias (nome, tipo, categoria_pai_id)
                    VALUES (:nome, :tipo, :categoria_pai_id)
                    RETURNING id
                    """
                ),
                {"nome": nome, "tipo": tipo, "categoria_pai_id": categoria_pai_id},
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar categoria.") from exc


def obter_categoria(id: int) -> dict | None:
    try:
        with obter_engine().connect() as conn:
            linha = conn.execute(
                text("SELECT * FROM categorias WHERE id = :id"), {"id": id}
            ).mappings().first()
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter categoria.") from exc


def listar_categorias(
    tipo: str | None = None, incluir_inativas: bool = False
) -> list[dict]:
    if tipo is not None:
        _validar_tipo(tipo)

    condicoes = []
    parametros: dict[str, object] = {}

    if not incluir_inativas:
        condicoes.append("ativa = true")
    if tipo is not None:
        condicoes.append("tipo = :tipo")
        parametros["tipo"] = tipo

    clausula_where = f" WHERE {' AND '.join(condicoes)}" if condicoes else ""
    consulta = text(f"SELECT * FROM categorias{clausula_where} ORDER BY nome")

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(consulta, parametros).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar categorias.") from exc


def atualizar_categoria(
    id: int,
    nome: str | None = None,
    tipo: str | None = None,
    categoria_pai_id=_NAO_INFORMADO,
    ativa: bool | None = None,
) -> None:
    if nome is not None:
        _validar_nome(nome)
    if tipo is not None:
        _validar_tipo(tipo)

    try:
        with obter_engine().begin() as conn:
            atual = conn.execute(
                text("SELECT tipo, categoria_pai_id FROM categorias WHERE id = :id"),
                {"id": id},
            ).mappings().first()
            if atual is None:
                raise ValueError(f"Categoria {id} não encontrada.")

            tipo_final = tipo if tipo is not None else atual["tipo"]
            pai_final = (
                categoria_pai_id
                if categoria_pai_id is not _NAO_INFORMADO
                else atual["categoria_pai_id"]
            )

            if pai_final is not None:
                _validar_pai(conn, pai_final, tipo_final, id_atual=id)

            campos: dict[str, object] = {}
            if nome is not None:
                campos["nome"] = nome
            if tipo is not None:
                campos["tipo"] = tipo
            if categoria_pai_id is not _NAO_INFORMADO:
                campos["categoria_pai_id"] = categoria_pai_id
            if ativa is not None:
                campos["ativa"] = ativa

            if not campos:
                return

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
            campos["id"] = id
            conn.execute(
                text(
                    f"UPDATE categorias SET {atribuicoes}, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                campos,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar categoria.") from exc


def excluir_categoria(id: int) -> None:
    try:
        with obter_engine().begin() as conn:
            tem_dependencias = conn.execute(
                text(
                    """
                    SELECT
                        EXISTS (SELECT 1 FROM transacoes WHERE categoria_id = :id)
                        OR EXISTS (
                            SELECT 1 FROM regras_categorizacao WHERE categoria_id = :id
                        )
                        OR EXISTS (
                            SELECT 1 FROM categorias WHERE categoria_pai_id = :id
                        )
                    """
                ),
                {"id": id},
            ).scalar_one()

            if tem_dependencias:
                resultado = conn.execute(
                    text(
                        "UPDATE categorias SET ativa = false, atualizado_em = now() "
                        "WHERE id = :id"
                    ),
                    {"id": id},
                )
            else:
                resultado = conn.execute(
                    text("DELETE FROM categorias WHERE id = :id"), {"id": id}
                )

            if resultado.rowcount == 0:
                raise ValueError(f"Categoria {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir categoria.") from exc
