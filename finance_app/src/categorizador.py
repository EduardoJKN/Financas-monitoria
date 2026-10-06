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


# ---------------------------------------------------------------------
# Aplicação retroativa de regras em lançamentos já existentes
# ---------------------------------------------------------------------
def buscar_transacoes_compativeis_regra(
    regra_id: int, somente_sem_categoria: bool = True
) -> list[dict]:
    """Lista transações já existentes cuja descrição corresponde à regra.

    Reaproveita exatamente a mesma comparação de _regra_corresponde usada em
    categorizar_descricao (mesmos operadores, mesma normalização). Nunca
    inclui transferências. Respeita a compatibilidade de tipo da categoria
    da regra (despesa -> só despesas; receita -> só receitas; ambos ->
    receitas e despesas). Regra inativa ou categoria inativa/inexistente
    sempre retornam lista vazia.
    """
    regra = obter_regra(regra_id)
    if regra is None:
        raise ValueError(f"Regra {regra_id} não encontrada.")
    if not regra["ativa"]:
        return []

    try:
        with obter_engine().connect() as conn:
            categoria = (
                conn.execute(
                    text("SELECT tipo, ativa FROM categorias WHERE id = :id"),
                    {"id": regra["categoria_id"]},
                )
                .mappings()
                .first()
            )

            if categoria is None or not categoria["ativa"]:
                return []

            tipos_aceitos = (
                ["receita", "despesa"] if categoria["tipo"] == "ambos" else [categoria["tipo"]]
            )
            placeholders = ", ".join(f":tipo{i}" for i in range(len(tipos_aceitos)))
            parametros: dict[str, object] = {
                f"tipo{i}": tipo for i, tipo in enumerate(tipos_aceitos)
            }

            condicoes = [f"tipo IN ({placeholders})"]
            if somente_sem_categoria:
                condicoes.append("categoria_id IS NULL")
            clausula_where = " AND ".join(condicoes)

            linhas = (
                conn.execute(
                    text(
                        f"SELECT * FROM transacoes WHERE {clausula_where} "
                        "ORDER BY data_transacao DESC, id DESC"
                    ),
                    parametros,
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao buscar lançamentos compatíveis com a regra.") from exc

    texto_regra = normalizar_texto(regra["texto_busca"])
    return [
        dict(linha)
        for linha in linhas
        if _regra_corresponde(regra["operador"], texto_regra, normalizar_texto(linha["descricao"]))
    ]


def aplicar_regra_em_transacoes_existentes(
    regra_id: int,
    transacao_ids: list[int] | None = None,
    somente_sem_categoria: bool = True,
) -> int:
    """Aplica a categoria da regra às transações informadas.

    Atualiza SOMENTE a coluna categoria_id — nenhum outro campo da transação
    é tocado. Operação atômica: todas as atualizações acontecem em uma única
    transação de banco (tudo ou nada).

    Por segurança, o conjunto de transações elegíveis é sempre recalculado
    via buscar_transacoes_compativeis_regra com o mesmo somente_sem_categoria
    recebido aqui — mesmo que `transacao_ids` inclua uma transação já
    categorizada, ela só será de fato atualizada se somente_sem_categoria for
    False (ou seja, a sobrescrita exige escolha explícita da chamada, nunca
    acontece por padrão).
    """
    if regra_id is None:
        raise ValueError("regra_id é obrigatório.")

    compativeis = buscar_transacoes_compativeis_regra(
        regra_id, somente_sem_categoria=somente_sem_categoria
    )
    if transacao_ids is None:
        alvo_ids = [t["id"] for t in compativeis]
    else:
        ids_compativeis = {t["id"] for t in compativeis}
        alvo_ids = [tid for tid in transacao_ids if tid in ids_compativeis]

    if not alvo_ids:
        return 0

    regra = obter_regra(regra_id)

    try:
        with obter_engine().begin() as conn:
            for tid in alvo_ids:
                conn.execute(
                    text(
                        "UPDATE transacoes SET categoria_id = :categoria_id, "
                        "atualizado_em = now() WHERE id = :id"
                    ),
                    {"categoria_id": regra["categoria_id"], "id": tid},
                )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados(
            "Falha ao aplicar a regra aos lançamentos existentes."
        ) from exc

    return len(alvo_ids)


def prever_aplicacao_todas_regras() -> list[dict]:
    """Para cada transação sem categoria (receita/despesa, nunca
    transferência), calcula a categoria sugerida usando categorizar_descricao
    — a mesma função usada em importações e novos lançamentos. Não altera o
    banco; apenas retorna o que SERIA feito.
    """
    try:
        with obter_engine().connect() as conn:
            candidatas = (
                conn.execute(
                    text(
                        "SELECT id, data_transacao, descricao, tipo, valor FROM transacoes "
                        "WHERE categoria_id IS NULL AND tipo IN ('receita', 'despesa') "
                        "ORDER BY data_transacao DESC, id DESC"
                    )
                )
                .mappings()
                .all()
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao buscar lançamentos sem categoria.") from exc

    resultado = []
    for linha in candidatas:
        categoria_sugerida_id = categorizar_descricao(linha["descricao"], linha["tipo"])
        if categoria_sugerida_id is not None:
            item = dict(linha)
            item["categoria_sugerida_id"] = categoria_sugerida_id
            resultado.append(item)
    return resultado


def aplicar_todas_regras_em_transacoes_sem_categoria(transacao_ids: list[int]) -> int:
    """Aplica, de forma atômica, a categoria sugerida por categorizar_descricao
    às transações informadas (pensado para receber os ids retornados por
    prever_aplicacao_todas_regras).

    Nunca sobrescreve uma transação que já tenha categoria: cada linha é
    reconferida (categoria_id IS NULL) dentro da própria transação de banco
    antes de ser atualizada, e a categoria é recalculada na hora (protege
    contra regras terem mudado entre a prévia e a confirmação). Atualiza
    somente categoria_id.
    """
    if not transacao_ids:
        return 0

    try:
        with obter_engine().begin() as conn:
            total = 0
            for tid in transacao_ids:
                atual = (
                    conn.execute(
                        text(
                            "SELECT descricao, tipo, categoria_id FROM transacoes WHERE id = :id"
                        ),
                        {"id": tid},
                    )
                    .mappings()
                    .first()
                )
                if atual is None or atual["categoria_id"] is not None:
                    continue  # nunca sobrescreve uma categoria já existente
                if atual["tipo"] not in ("receita", "despesa"):
                    continue  # nunca categoriza transferência

                categoria_id = categorizar_descricao(atual["descricao"], atual["tipo"])
                if categoria_id is None:
                    continue

                conn.execute(
                    text(
                        "UPDATE transacoes SET categoria_id = :categoria_id, "
                        "atualizado_em = now() WHERE id = :id"
                    ),
                    {"categoria_id": categoria_id, "id": tid},
                )
                total += 1
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados(
            "Falha ao aplicar as regras aos lançamentos existentes."
        ) from exc

    return total
