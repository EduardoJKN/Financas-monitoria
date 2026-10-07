"""Lançamentos recorrentes (tabela recorrencias).

A geração de lançamentos pendentes é idempotente: cada execução avança
`proxima_data` para além da última ocorrência gerada, então rodar a ação
duas vezes no mesmo dia não duplica lançamentos.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, conexao_usuario
from src.datas import avancar_anos, avancar_meses

PERIODICIDADES = {"mensal", "semanal", "anual"}
_NAO_INFORMADO = object()


def _validar_tipo(tipo: str) -> None:
    if tipo not in ("receita", "despesa"):
        raise ValueError("tipo deve ser 'receita' ou 'despesa'.")


def _validar_descricao(descricao: str) -> None:
    if not descricao or not descricao.strip():
        raise ValueError("A descrição da recorrência não pode ser vazia.")


def _validar_valor(valor: Decimal) -> None:
    if not isinstance(valor, Decimal):
        raise ValueError("valor deve ser do tipo Decimal.")
    if valor <= 0:
        raise ValueError("valor deve ser maior que zero.")


def _validar_periodicidade(periodicidade: str) -> None:
    if periodicidade not in PERIODICIDADES:
        raise ValueError(
            f"Periodicidade inválida: '{periodicidade}'. "
            f"Use uma de {sorted(PERIODICIDADES)}."
        )


def _validar_datas(data_inicio: date, data_fim: date | None) -> None:
    if not isinstance(data_inicio, date):
        raise ValueError("data_inicio deve ser um objeto date.")
    if data_fim is not None and data_fim < data_inicio:
        raise ValueError("data_fim não pode ser anterior a data_inicio.")


def _validar_conta_ativa(conn: Connection, conta_id: int) -> None:
    conta = (
        conn.execute(text("SELECT ativa FROM contas WHERE id = :id"), {"id": conta_id})
        .mappings()
        .first()
    )
    if conta is None:
        raise ValueError(f"Conta {conta_id} não encontrada.")
    if not conta["ativa"]:
        raise ValueError(f"Conta {conta_id} está inativa.")


def _validar_categoria_ativa(conn: Connection, categoria_id: int, tipo: str) -> None:
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
    if categoria["tipo"] not in ("ambos", tipo):
        raise ValueError(
            f"Categoria do tipo '{categoria['tipo']}' incompatível com recorrência "
            f"do tipo '{tipo}'."
        )


def _data_ocorrencia(data_inicio: date, periodicidade: str, indice: int) -> date:
    """Data da ocorrência de índice `indice` (0-based) a partir de data_inicio.

    Sempre ancorada em data_inicio (nunca na ocorrência anterior), para que
    um mês mais curto não "puxe" o dia das ocorrências seguintes para baixo
    permanentemente. Ex.: data_inicio=31/01 gera 31/01, 28/02, 31/03, 30/04,
    31/05 — nunca 28/03 por causa de fevereiro.
    """
    if periodicidade == "semanal":
        return data_inicio + timedelta(days=7 * indice)
    if periodicidade == "anual":
        return avancar_anos(data_inicio, indice)
    return avancar_meses(data_inicio, indice)  # mensal


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------
def criar_recorrencia(
    tipo: str,
    descricao: str,
    valor: Decimal,
    conta_id: int,
    periodicidade: str,
    data_inicio: date,
    categoria_id: int | None = None,
    observacao: str | None = None,
    data_fim: date | None = None,
) -> int:
    _validar_tipo(tipo)
    _validar_descricao(descricao)
    _validar_valor(valor)
    _validar_periodicidade(periodicidade)
    _validar_datas(data_inicio, data_fim)

    try:
        with conexao_usuario() as conn:
            _validar_conta_ativa(conn, conta_id)
            if categoria_id is not None:
                _validar_categoria_ativa(conn, categoria_id, tipo)

            resultado = conn.execute(
                text(
                    """
                    INSERT INTO recorrencias (
                        tipo, descricao, valor, categoria_id, conta_id, observacao,
                        periodicidade, data_inicio, data_fim, proxima_data, ativa
                    ) VALUES (
                        :tipo, :descricao, :valor, :categoria_id, :conta_id, :observacao,
                        :periodicidade, :data_inicio, :data_fim, :proxima_data, true
                    )
                    RETURNING id
                    """
                ),
                {
                    "tipo": tipo,
                    "descricao": descricao.strip(),
                    "valor": valor,
                    "categoria_id": categoria_id,
                    "conta_id": conta_id,
                    "observacao": observacao,
                    "periodicidade": periodicidade,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                    "proxima_data": data_inicio,
                },
            )
            return resultado.scalar_one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao criar recorrência.") from exc


def obter_recorrencia(id: int) -> dict | None:
    try:
        with conexao_usuario() as conn:
            linha = (
                conn.execute(text("SELECT * FROM recorrencias WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter recorrência.") from exc


def listar_recorrencias(incluir_inativas: bool = False) -> list[dict]:
    if incluir_inativas:
        consulta = text("SELECT * FROM recorrencias ORDER BY descricao")
    else:
        consulta = text(
            "SELECT * FROM recorrencias WHERE ativa = true ORDER BY descricao"
        )
    try:
        with conexao_usuario() as conn:
            linhas = conn.execute(consulta).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar recorrências.") from exc


def atualizar_recorrencia(
    id: int,
    tipo: str | None = None,
    descricao: str | None = None,
    valor: Decimal | None = None,
    conta_id: int | None = None,
    categoria_id=_NAO_INFORMADO,
    periodicidade: str | None = None,
    data_inicio: date | None = None,
    data_fim=_NAO_INFORMADO,
    ativa: bool | None = None,
) -> None:
    if tipo is not None:
        _validar_tipo(tipo)
    if descricao is not None:
        _validar_descricao(descricao)
    if valor is not None:
        _validar_valor(valor)
    if periodicidade is not None:
        _validar_periodicidade(periodicidade)

    try:
        with conexao_usuario() as conn:
            atual = (
                conn.execute(text("SELECT * FROM recorrencias WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            if atual is None:
                raise ValueError(f"Recorrência {id} não encontrada.")

            estado_final = {
                "tipo": tipo if tipo is not None else atual["tipo"],
                "descricao": descricao.strip() if descricao is not None else atual["descricao"],
                "valor": valor if valor is not None else atual["valor"],
                "conta_id": conta_id if conta_id is not None else atual["conta_id"],
                "categoria_id": (
                    categoria_id if categoria_id is not _NAO_INFORMADO else atual["categoria_id"]
                ),
                "periodicidade": (
                    periodicidade if periodicidade is not None else atual["periodicidade"]
                ),
                "data_inicio": (
                    data_inicio if data_inicio is not None else atual["data_inicio"]
                ),
                "data_fim": (
                    data_fim if data_fim is not _NAO_INFORMADO else atual["data_fim"]
                ),
                "ativa": ativa if ativa is not None else atual["ativa"],
            }
            _validar_datas(estado_final["data_inicio"], estado_final["data_fim"])
            _validar_conta_ativa(conn, estado_final["conta_id"])
            if estado_final["categoria_id"] is not None:
                _validar_categoria_ativa(
                    conn, estado_final["categoria_id"], estado_final["tipo"]
                )

            atribuicoes = ", ".join(f"{coluna} = :{coluna}" for coluna in estado_final)
            estado_final["id"] = id
            conn.execute(
                text(
                    f"UPDATE recorrencias SET {atribuicoes}, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                estado_final,
            )
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao atualizar recorrência.") from exc


def desativar_recorrencia(id: int) -> None:
    atualizar_recorrencia(id, ativa=False)


def excluir_recorrencia(id: int) -> None:
    """Exclui a recorrência. Se houver transações vinculadas (recorrencia_id),
    desativa em vez de excluir, preservando o histórico dos lançamentos já
    gerados."""
    try:
        with conexao_usuario() as conn:
            tem_transacoes = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM transacoes WHERE recorrencia_id = :id)"),
                {"id": id},
            ).scalar_one()

            if tem_transacoes:
                resultado = conn.execute(
                    text(
                        "UPDATE recorrencias SET ativa = false, atualizado_em = now() "
                        "WHERE id = :id"
                    ),
                    {"id": id},
                )
            else:
                resultado = conn.execute(
                    text("DELETE FROM recorrencias WHERE id = :id"), {"id": id}
                )

            if resultado.rowcount == 0:
                raise ValueError(f"Recorrência {id} não encontrada.")
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao excluir recorrência.") from exc


# ---------------------------------------------------------------------
# Geração de lançamentos pendentes (idempotente)
# ---------------------------------------------------------------------
def gerar_lancamentos_pendentes(hoje: date | None = None) -> dict:
    """Gera todos os lançamentos ainda não criados (proxima_data <= hoje)
    para todas as recorrências ativas.

    Idempotente: o índice da próxima ocorrência de cada recorrência é
    recalculado a partir da contagem de transações já geradas para ela
    (COUNT(*) WHERE recorrencia_id = id), então rodar a ação duas vezes não
    duplica nada — na segunda vez a contagem já reflete o que foi inserido
    na primeira.

    Retorna um resumo: quantidade total gerada e por recorrência.
    """
    referencia = hoje if hoje is not None else date.today()

    try:
        with conexao_usuario() as conn:
            recorrencias_ativas = (
                conn.execute(
                    text(
                        "SELECT * FROM recorrencias WHERE ativa = true "
                        "AND proxima_data <= :hoje ORDER BY id"
                    ),
                    {"hoje": referencia},
                )
                .mappings()
                .all()
            )

            gerados_por_recorrencia: dict[int, int] = {}
            total_gerado = 0

            for recorrencia in recorrencias_ativas:
                data_inicio = recorrencia["data_inicio"]
                data_fim = recorrencia["data_fim"]
                periodicidade = recorrencia["periodicidade"]

                indice = conn.execute(
                    text("SELECT COUNT(*) FROM transacoes WHERE recorrencia_id = :id"),
                    {"id": recorrencia["id"]},
                ).scalar_one()

                quantidade_desta = 0
                data_candidata = _data_ocorrencia(data_inicio, periodicidade, indice)

                while data_candidata <= referencia and (
                    data_fim is None or data_candidata <= data_fim
                ):
                    conn.execute(
                        text(
                            """
                            INSERT INTO transacoes (
                                tipo, descricao, valor, data_transacao, categoria_id,
                                conta_id, observacao, origem, recorrencia_id
                            ) VALUES (
                                :tipo, :descricao, :valor, :data_transacao, :categoria_id,
                                :conta_id, :observacao, 'recorrencia', :recorrencia_id
                            )
                            """
                        ),
                        {
                            "tipo": recorrencia["tipo"],
                            "descricao": recorrencia["descricao"],
                            "valor": recorrencia["valor"],
                            "data_transacao": data_candidata,
                            "categoria_id": recorrencia["categoria_id"],
                            "conta_id": recorrencia["conta_id"],
                            "observacao": recorrencia["observacao"],
                            "recorrencia_id": recorrencia["id"],
                        },
                    )
                    quantidade_desta += 1
                    total_gerado += 1
                    indice += 1
                    data_candidata = _data_ocorrencia(data_inicio, periodicidade, indice)

                nova_ativa = recorrencia["ativa"]
                if data_fim is not None and data_candidata > data_fim:
                    nova_ativa = False

                conn.execute(
                    text(
                        "UPDATE recorrencias SET proxima_data = :proxima_data, "
                        "ativa = :ativa, atualizado_em = now() WHERE id = :id"
                    ),
                    {
                        "proxima_data": data_candidata,
                        "ativa": nova_ativa,
                        "id": recorrencia["id"],
                    },
                )

                if quantidade_desta > 0:
                    gerados_por_recorrencia[recorrencia["id"]] = quantidade_desta

            return {
                "total_gerado": total_gerado,
                "por_recorrencia": gerados_por_recorrencia,
            }
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao gerar lançamentos recorrentes.") from exc
