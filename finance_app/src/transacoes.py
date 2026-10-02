import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, obter_engine

TIPOS_TRANSACAO = {"receita", "despesa", "transferencia"}
ORIGENS_TRANSACAO = {"manual", "importacao"}

_NAO_INFORMADO = object()


# ---------------------------------------------------------------------
# Validações de campos simples (não tocam o banco)
# ---------------------------------------------------------------------
def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_TRANSACAO:
        raise ValueError(
            f"Tipo de transação inválido: '{tipo}'. Tipos aceitos: {sorted(TIPOS_TRANSACAO)}."
        )


def _validar_origem(origem: str) -> None:
    if origem not in ORIGENS_TRANSACAO:
        raise ValueError(
            f"Origem inválida: '{origem}'. Origens aceitas: {sorted(ORIGENS_TRANSACAO)}."
        )


def _validar_descricao(descricao: str) -> None:
    if not descricao or not descricao.strip():
        raise ValueError("A descrição da transação não pode ser vazia.")


def _validar_valor(valor: Decimal) -> None:
    if not isinstance(valor, Decimal):
        raise ValueError("valor deve ser do tipo Decimal.")
    if valor <= 0:
        raise ValueError("valor deve ser maior que zero.")


def _validar_data(data_transacao: date) -> None:
    if not isinstance(data_transacao, date):
        raise ValueError("data_transacao deve ser um objeto date.")


def _validar_parcelamento(
    numero_parcela: int | None,
    total_parcelas: int | None,
    grupo_parcelamento: uuid.UUID | None,
) -> None:
    campos = (numero_parcela, total_parcelas, grupo_parcelamento)
    if all(campo is None for campo in campos):
        return
    if not all(campo is not None for campo in campos):
        raise ValueError(
            "numero_parcela, total_parcelas e grupo_parcelamento devem ser "
            "todos preenchidos ou todos omitidos."
        )
    if (
        not isinstance(numero_parcela, int)
        or isinstance(numero_parcela, bool)
        or numero_parcela <= 0
    ):
        raise ValueError("numero_parcela deve ser um inteiro positivo.")
    if (
        not isinstance(total_parcelas, int)
        or isinstance(total_parcelas, bool)
        or total_parcelas <= 0
    ):
        raise ValueError("total_parcelas deve ser um inteiro positivo.")
    if numero_parcela > total_parcelas:
        raise ValueError("numero_parcela não pode ser maior que total_parcelas.")
    if not isinstance(grupo_parcelamento, uuid.UUID):
        raise ValueError("grupo_parcelamento deve ser um UUID.")


# ---------------------------------------------------------------------
# Validações que dependem do banco (conta/categoria)
# ---------------------------------------------------------------------
def _validar_conta_ativa(conn: Connection, conta_id: int, campo: str) -> None:
    conta = conn.execute(
        text("SELECT ativa FROM contas WHERE id = :id"), {"id": conta_id}
    ).mappings().first()
    if conta is None:
        raise ValueError(f"{campo}: conta {conta_id} não encontrada.")
    if not conta["ativa"]:
        raise ValueError(f"{campo}: conta {conta_id} está inativa.")


def _validar_categoria_ativa(conn: Connection, categoria_id: int) -> dict:
    categoria = conn.execute(
        text("SELECT tipo, ativa FROM categorias WHERE id = :id"), {"id": categoria_id}
    ).mappings().first()
    if categoria is None:
        raise ValueError(f"Categoria {categoria_id} não encontrada.")
    if not categoria["ativa"]:
        raise ValueError(f"Categoria {categoria_id} está inativa.")
    return dict(categoria)


def _tipo_categoria_compativel(tipo_categoria: str, tipo_transacao: str) -> bool:
    return tipo_categoria == "ambos" or tipo_categoria == tipo_transacao


def _validar_contas_e_categoria(
    conn: Connection,
    tipo: str,
    conta_id: int,
    conta_destino_id: int | None,
    categoria_id: int | None,
) -> None:
    _validar_conta_ativa(conn, conta_id, "conta_id")

    if tipo == "transferencia":
        if conta_destino_id is None:
            raise ValueError("Transferência exige conta_destino_id.")
        if conta_destino_id == conta_id:
            raise ValueError(
                "conta_destino_id deve ser diferente de conta_id em uma transferência."
            )
        _validar_conta_ativa(conn, conta_destino_id, "conta_destino_id")
        if categoria_id is not None:
            raise ValueError("Transferência não pode ter categoria_id.")
    else:
        if conta_destino_id is not None:
            raise ValueError(f"conta_destino_id deve ser None para tipo '{tipo}'.")
        if categoria_id is not None:
            categoria = _validar_categoria_ativa(conn, categoria_id)
            if not _tipo_categoria_compativel(categoria["tipo"], tipo):
                raise ValueError(
                    f"Categoria do tipo '{categoria['tipo']}' incompatível com "
                    f"transação do tipo '{tipo}'."
                )


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def criar_transacao(
    tipo: str,
    descricao: str,
    valor: Decimal,
    data_transacao: date,
    conta_id: int,
    conta_destino_id: int | None = None,
    categoria_id: int | None = None,
    origem: str = "manual",
    observacao: str | None = None,
    grupo_parcelamento: uuid.UUID | None = None,
    numero_parcela: int | None = None,
    total_parcelas: int | None = None,
) -> int:
    _validar_tipo(tipo)
    _validar_origem(origem)
    _validar_descricao(descricao)
    _validar_valor(valor)
    _validar_data(data_transacao)
    _validar_parcelamento(numero_parcela, total_parcelas, grupo_parcelamento)

    try:
        with obter_engine().begin() as conn:
            _validar_contas_e_categoria(conn, tipo, conta_id, conta_destino_id, categoria_id)

            resultado = conn.execute(
                text(
                    """
                    INSERT INTO transacoes (
                        tipo, descricao, valor, data_transacao, categoria_id,
                        conta_id, conta_destino_id, observacao, origem,
                        grupo_parcelamento, numero_parcela, total_parcelas
                    ) VALUES (
                        :tipo, :descricao, :valor, :data_transacao, :categoria_id,
                        :conta_id, :conta_destino_id, :observacao, :origem,
                        :grupo_parcelamento, :numero_parcela, :total_parcelas
                    )
                    RETURNING id
                    """
                ),
                {
                    "tipo": tipo,
                    "descricao": descricao,
                    "valor": valor,
                    "data_transacao": data_transacao,
                    "categoria_id": categoria_id,
                    "conta_id": conta_id,
                    "conta_destino_id": conta_destino_id,
                    "observacao": observacao,
                    "origem": origem,
                    "grupo_parcelamento": grupo_parcelamento,
                    "numero_parcela": numero_parcela,
                    "total_parcelas": total_parcelas,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar transação.") from exc


def obter_transacao(id: int) -> dict | None:
    try:
        with obter_engine().connect() as conn:
            linha = conn.execute(
                text("SELECT * FROM transacoes WHERE id = :id"), {"id": id}
            ).mappings().first()
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter transação.") from exc


def listar_transacoes(
    tipo: str | None = None,
    conta_id: int | None = None,
    categoria_id: int | None = None,
    origem: str | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
    texto_busca: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict]:
    if tipo is not None:
        _validar_tipo(tipo)
    if origem is not None:
        _validar_origem(origem)

    condicoes = []
    parametros: dict[str, object] = {}

    if tipo is not None:
        condicoes.append("tipo = :tipo")
        parametros["tipo"] = tipo
    if conta_id is not None:
        condicoes.append("(conta_id = :conta_id OR conta_destino_id = :conta_id)")
        parametros["conta_id"] = conta_id
    if categoria_id is not None:
        condicoes.append("categoria_id = :categoria_id")
        parametros["categoria_id"] = categoria_id
    if origem is not None:
        condicoes.append("origem = :origem")
        parametros["origem"] = origem
    if data_inicial is not None:
        condicoes.append("data_transacao >= :data_inicial")
        parametros["data_inicial"] = data_inicial
    if data_final is not None:
        condicoes.append("data_transacao <= :data_final")
        parametros["data_final"] = data_final
    if texto_busca is not None and texto_busca.strip():
        condicoes.append("descricao ILIKE :texto_busca")
        parametros["texto_busca"] = f"%{texto_busca.strip()}%"

    clausula_where = f" WHERE {' AND '.join(condicoes)}" if condicoes else ""

    clausula_paginacao = ""
    if limit is not None:
        clausula_paginacao += " LIMIT :limit"
        parametros["limit"] = limit
    if offset is not None:
        clausula_paginacao += " OFFSET :offset"
        parametros["offset"] = offset

    consulta = text(
        f"SELECT * FROM transacoes{clausula_where} "
        f"ORDER BY data_transacao DESC, id DESC{clausula_paginacao}"
    )

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(consulta, parametros).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar transações.") from exc


def atualizar_transacao(
    id: int,
    tipo: str | None = None,
    descricao: str | None = None,
    valor: Decimal | None = None,
    data_transacao: date | None = None,
    conta_id: int | None = None,
    conta_destino_id=_NAO_INFORMADO,
    categoria_id=_NAO_INFORMADO,
    origem: str | None = None,
    observacao=_NAO_INFORMADO,
    grupo_parcelamento=_NAO_INFORMADO,
    numero_parcela=_NAO_INFORMADO,
    total_parcelas=_NAO_INFORMADO,
) -> None:
    try:
        with obter_engine().begin() as conn:
            atual = conn.execute(
                text("SELECT * FROM transacoes WHERE id = :id"), {"id": id}
            ).mappings().first()
            if atual is None:
                raise ValueError(f"Transação {id} não encontrada.")

            estado_final = {
                "tipo": tipo if tipo is not None else atual["tipo"],
                "descricao": descricao if descricao is not None else atual["descricao"],
                "valor": valor if valor is not None else atual["valor"],
                "data_transacao": (
                    data_transacao if data_transacao is not None else atual["data_transacao"]
                ),
                "conta_id": conta_id if conta_id is not None else atual["conta_id"],
                "conta_destino_id": (
                    conta_destino_id
                    if conta_destino_id is not _NAO_INFORMADO
                    else atual["conta_destino_id"]
                ),
                "categoria_id": (
                    categoria_id if categoria_id is not _NAO_INFORMADO else atual["categoria_id"]
                ),
                "origem": origem if origem is not None else atual["origem"],
                "observacao": (
                    observacao if observacao is not _NAO_INFORMADO else atual["observacao"]
                ),
                "grupo_parcelamento": (
                    grupo_parcelamento
                    if grupo_parcelamento is not _NAO_INFORMADO
                    else atual["grupo_parcelamento"]
                ),
                "numero_parcela": (
                    numero_parcela
                    if numero_parcela is not _NAO_INFORMADO
                    else atual["numero_parcela"]
                ),
                "total_parcelas": (
                    total_parcelas
                    if total_parcelas is not _NAO_INFORMADO
                    else atual["total_parcelas"]
                ),
            }

            _validar_tipo(estado_final["tipo"])
            _validar_origem(estado_final["origem"])
            _validar_descricao(estado_final["descricao"])
            _validar_valor(estado_final["valor"])
            _validar_data(estado_final["data_transacao"])
            _validar_parcelamento(
                estado_final["numero_parcela"],
                estado_final["total_parcelas"],
                estado_final["grupo_parcelamento"],
            )
            _validar_contas_e_categoria(
                conn,
                estado_final["tipo"],
                estado_final["conta_id"],
                estado_final["conta_destino_id"],
                estado_final["categoria_id"],
            )

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in estado_final)
            estado_final["id"] = id
            conn.execute(
                text(
                    f"UPDATE transacoes SET {atribuicoes}, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                estado_final,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar transação.") from exc


def excluir_transacao(id: int) -> None:
    try:
        with obter_engine().begin() as conn:
            resultado = conn.execute(
                text("DELETE FROM transacoes WHERE id = :id"), {"id": id}
            )
            if resultado.rowcount == 0:
                raise ValueError(f"Transação {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir transação.") from exc
