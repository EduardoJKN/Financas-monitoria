from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src import categorias as categorias_modulo
from src.banco_de_dados import ErroBancoDeDados, obter_engine

TIPOS_RESUMO_CATEGORIA = {"receita", "despesa"}
PERIODOS_VALIDOS = {"este_mes", "mes_passado", "ultimos_30_dias", "este_ano"}

# Saldo de cada conta = saldo_inicial + receitas - despesas
#                        + transferências recebidas - transferências enviadas.
# Contas inativas não são filtradas aqui de propósito: elas continuam
# participando de cálculos históricos, pois podem ter transações associadas.
_SQL_SALDOS = """
    WITH movimentos AS (
        SELECT
            conta_id,
            CASE
                WHEN tipo = 'receita' THEN valor
                WHEN tipo = 'despesa' THEN -valor
                WHEN tipo = 'transferencia' THEN -valor
            END AS efeito,
            data_transacao
        FROM transacoes
        WHERE conta_id IS NOT NULL
        UNION ALL
        SELECT
            conta_destino_id AS conta_id,
            valor AS efeito,
            data_transacao
        FROM transacoes
        WHERE tipo = 'transferencia' AND conta_destino_id IS NOT NULL
    ),
    agregado AS (
        SELECT conta_id, SUM(efeito) AS total
        FROM movimentos
        WHERE :ate_data IS NULL OR data_transacao <= :ate_data
        GROUP BY conta_id
    )
    SELECT
        c.id AS conta_id,
        c.nome,
        c.ativa,
        c.saldo_inicial + COALESCE(a.total, 0) AS saldo
    FROM contas c
    LEFT JOIN agregado a ON a.conta_id = c.id
    WHERE :conta_id IS NULL OR c.id = :conta_id
    ORDER BY c.nome
"""


def _validar_data_opcional(valor: date | None, nome_campo: str) -> None:
    if valor is not None and not isinstance(valor, date):
        raise ValueError(f"{nome_campo} deve ser um objeto date.")


def _construir_mapa_categorias() -> dict[int, dict]:
    todas = categorias_modulo.listar_categorias(incluir_inativas=True)
    return {categoria["id"]: categoria for categoria in todas}


def _caminho_categoria(categoria_id: int | None, mapa: dict[int, dict]) -> str:
    if categoria_id is None:
        return "Sem categoria"
    partes = []
    visitados = set()
    atual_id = categoria_id
    while atual_id is not None and atual_id not in visitados:
        categoria = mapa.get(atual_id)
        if categoria is None:
            break
        visitados.add(atual_id)
        partes.append(categoria["nome"])
        atual_id = categoria["categoria_pai_id"]
    return " > ".join(reversed(partes)) if partes else "Sem categoria"


def calcular_intervalo_periodo(
    periodo: str, hoje: date | None = None
) -> tuple[date, date]:
    """Converte um período nomeado em (data_inicial, data_final), ambas inclusivas.

    Períodos personalizados não passam por aqui: a página monta o intervalo
    diretamente a partir de dois seletores de data.
    """
    if periodo not in PERIODOS_VALIDOS:
        raise ValueError(
            f"Período inválido: '{periodo}'. Use um de {sorted(PERIODOS_VALIDOS)}."
        )

    referencia = hoje if hoje is not None else date.today()

    if periodo == "este_mes":
        return referencia.replace(day=1), referencia
    if periodo == "ultimos_30_dias":
        return referencia - timedelta(days=29), referencia
    if periodo == "este_ano":
        return referencia.replace(month=1, day=1), referencia

    # mes_passado
    primeiro_dia_mes_atual = referencia.replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    return ultimo_dia_mes_passado.replace(day=1), ultimo_dia_mes_passado


def calcular_saldo_conta(conta_id: int, ate_data: date | None = None) -> Decimal:
    _validar_data_opcional(ate_data, "ate_data")
    try:
        with obter_engine().connect() as conn:
            linha = conn.execute(
                text(_SQL_SALDOS), {"ate_data": ate_data, "conta_id": conta_id}
            ).mappings().first()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular saldo da conta.") from exc

    if linha is None:
        raise ValueError(f"Conta {conta_id} não encontrada.")
    return linha["saldo"]


def calcular_saldos_contas(ate_data: date | None = None) -> list[dict]:
    _validar_data_opcional(ate_data, "ate_data")
    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(
                text(_SQL_SALDOS), {"ate_data": ate_data, "conta_id": None}
            ).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular saldos das contas.") from exc


def calcular_saldo_total(ate_data: date | None = None) -> Decimal:
    saldos = calcular_saldos_contas(ate_data=ate_data)
    total = Decimal("0")
    for linha in saldos:
        total += linha["saldo"]
    return total


def calcular_resumo_periodo(
    data_inicial: date | None = None,
    data_final: date | None = None,
    conta_id: int | None = None,
) -> dict:
    _validar_data_opcional(data_inicial, "data_inicial")
    _validar_data_opcional(data_final, "data_final")

    sql = text(
        """
        SELECT
            COALESCE(SUM(
                CASE WHEN tipo = 'receita'
                     AND (:conta_id IS NULL OR conta_id = :conta_id)
                     THEN valor END
            ), 0) AS total_receitas,
            COALESCE(SUM(
                CASE WHEN tipo = 'despesa'
                     AND (:conta_id IS NULL OR conta_id = :conta_id)
                     THEN valor END
            ), 0) AS total_despesas,
            COALESCE(SUM(
                CASE WHEN tipo = 'transferencia'
                     AND (:conta_id IS NULL OR conta_id = :conta_id)
                     THEN valor END
            ), 0) AS total_transferencias_enviadas,
            COALESCE(SUM(
                CASE WHEN tipo = 'transferencia'
                     AND (:conta_id IS NULL OR conta_destino_id = :conta_id)
                     THEN valor END
            ), 0) AS total_transferencias_recebidas
        FROM transacoes
        WHERE (:data_inicial IS NULL OR data_transacao >= :data_inicial)
          AND (:data_final IS NULL OR data_transacao <= :data_final)
        """
    )
    params = {"conta_id": conta_id, "data_inicial": data_inicial, "data_final": data_final}

    try:
        with obter_engine().connect() as conn:
            linha = conn.execute(sql, params).mappings().one()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular resumo do período.") from exc

    total_receitas = linha["total_receitas"]
    total_despesas = linha["total_despesas"]
    return {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "resultado": total_receitas - total_despesas,
        "total_transferencias_enviadas": linha["total_transferencias_enviadas"],
        "total_transferencias_recebidas": linha["total_transferencias_recebidas"],
    }


def resumir_por_categoria(
    data_inicial: date | None = None,
    data_final: date | None = None,
    tipo: str | None = None,
    conta_id: int | None = None,
) -> list[dict]:
    _validar_data_opcional(data_inicial, "data_inicial")
    _validar_data_opcional(data_final, "data_final")
    if tipo is not None and tipo not in TIPOS_RESUMO_CATEGORIA:
        raise ValueError(
            f"Tipo inválido para resumo por categoria: '{tipo}'. "
            f"Use 'receita' ou 'despesa' (transferências não entram neste resumo)."
        )

    sql = text(
        """
        SELECT categoria_id, tipo, SUM(valor) AS total
        FROM transacoes
        WHERE tipo IN ('receita', 'despesa')
          AND (:tipo IS NULL OR tipo = :tipo)
          AND (:conta_id IS NULL OR conta_id = :conta_id)
          AND (:data_inicial IS NULL OR data_transacao >= :data_inicial)
          AND (:data_final IS NULL OR data_transacao <= :data_final)
        GROUP BY categoria_id, tipo
        ORDER BY tipo, total DESC
        """
    )
    params = {
        "tipo": tipo,
        "conta_id": conta_id,
        "data_inicial": data_inicial,
        "data_final": data_final,
    }

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(sql, params).mappings().all()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular resumo por categoria.") from exc

    mapa_categorias = _construir_mapa_categorias()
    return [
        {
            "categoria_id": linha["categoria_id"],
            "categoria": _caminho_categoria(linha["categoria_id"], mapa_categorias),
            "tipo": linha["tipo"],
            "total": linha["total"],
        }
        for linha in linhas
    ]


def resumir_por_mes(
    data_inicial: date | None = None,
    data_final: date | None = None,
    conta_id: int | None = None,
) -> list[dict]:
    _validar_data_opcional(data_inicial, "data_inicial")
    _validar_data_opcional(data_final, "data_final")

    sql = text(
        """
        SELECT
            date_trunc('month', data_transacao)::date AS mes,
            COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor END), 0) AS total_receitas,
            COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor END), 0) AS total_despesas
        FROM transacoes
        WHERE tipo IN ('receita', 'despesa')
          AND (:conta_id IS NULL OR conta_id = :conta_id)
          AND (:data_inicial IS NULL OR data_transacao >= :data_inicial)
          AND (:data_final IS NULL OR data_transacao <= :data_final)
        GROUP BY 1
        ORDER BY 1
        """
    )
    params = {"conta_id": conta_id, "data_inicial": data_inicial, "data_final": data_final}

    try:
        with obter_engine().connect() as conn:
            linhas = conn.execute(sql, params).mappings().all()
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular resumo mensal.") from exc

    resultado = []
    for linha in linhas:
        total_receitas = linha["total_receitas"]
        total_despesas = linha["total_despesas"]
        resultado.append(
            {
                "mes": linha["mes"],
                "total_receitas": total_receitas,
                "total_despesas": total_despesas,
                "resultado": total_receitas - total_despesas,
            }
        )
    return resultado
