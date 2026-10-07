"""Faturas de cartão de crédito e pagamentos (faturas_cartao, pagamentos_fatura).

REGRA DE FECHAMENTO (documentada explicitamente, V1):
Uma compra feita NO PRÓPRIO DIA do fechamento ainda entra na fatura que está
fechando naquele dia — ou seja, o fechamento é tratado como acontecendo "no
fim do dia". Uma compra feita no dia seguinte ao fechamento já entra na
próxima fatura.

REGRA DE VENCIMENTO (V1):
Se dia_vencimento > dia_fechamento, o vencimento cai no mesmo mês do
fechamento (ex.: fecha dia 1, vence dia 10). Caso contrário, o vencimento
cai no mês seguinte ao fechamento (ex.: fecha dia 25, vence dia 5 do mês
seguinte). Dias inválidos para o mês (ex.: dia 31 em abril) são ajustados
para o último dia do mês.

Status da fatura: 'paga' e 'parcial' são persistidos (dependem de
pagamentos reais). 'aberta' vs 'fechada' é apenas uma questão de data atual
vs data_fechamento e é calculada sob demanda em status_exibicao_fatura, sem
depender de nenhum job agendado.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.banco_de_dados import ErroBancoDeDados, conexao_usuario
from src.datas import dia_valido_no_mes

STATUS_FATURA = {"aberta", "fechada", "paga", "parcial"}


# ---------------------------------------------------------------------
# Cálculo de datas (puro, sem banco)
# ---------------------------------------------------------------------
def calcular_mes_referencia(dia_fechamento: int, data_compra: date) -> date:
    """Primeiro dia do mês de referência da fatura à qual a compra pertence."""
    if data_compra.day <= dia_fechamento:
        return data_compra.replace(day=1)
    mes = data_compra.month % 12 + 1
    ano = data_compra.year + (1 if data_compra.month == 12 else 0)
    return date(ano, mes, 1)


def calcular_datas_fatura(
    dia_fechamento: int, dia_vencimento: int, mes_referencia: date
) -> tuple[date, date]:
    """Retorna (data_fechamento, data_vencimento) para a fatura de mes_referencia."""
    ano_fechamento = mes_referencia.year
    mes_fechamento = mes_referencia.month
    dia_fechamento_valido = dia_valido_no_mes(ano_fechamento, mes_fechamento, dia_fechamento)
    data_fechamento = date(ano_fechamento, mes_fechamento, dia_fechamento_valido)

    if dia_vencimento > dia_fechamento:
        ano_vencimento, mes_vencimento = ano_fechamento, mes_fechamento
    else:
        mes_vencimento = mes_fechamento % 12 + 1
        ano_vencimento = ano_fechamento + (1 if mes_fechamento == 12 else 0)
    dia_vencimento_valido = dia_valido_no_mes(ano_vencimento, mes_vencimento, dia_vencimento)
    data_vencimento = date(ano_vencimento, mes_vencimento, dia_vencimento_valido)

    return data_fechamento, data_vencimento


def status_exibicao_fatura(fatura: dict, hoje: date | None = None) -> str:
    """Status para exibição: 'paga'/'parcial' vêm do banco (dependem de
    pagamentos reais); 'aberta'/'fechada' são calculados a partir da data
    atual, sem necessidade de job agendado."""
    if fatura["status"] in ("paga", "parcial"):
        return fatura["status"]
    referencia = hoje if hoje is not None else date.today()
    return "fechada" if referencia > fatura["data_fechamento"] else "aberta"


# ---------------------------------------------------------------------
# Resolução de fatura (precisa de conexão/transação já aberta)
# ---------------------------------------------------------------------
def _obter_fatura_conn(conn: Connection, id: int) -> dict:
    linha = (
        conn.execute(text("SELECT * FROM faturas_cartao WHERE id = :id"), {"id": id})
        .mappings()
        .first()
    )
    return dict(linha)


def obter_ou_criar_fatura(conn: Connection, cartao: dict, data_compra: date) -> dict:
    """Encontra (ou cria) a fatura correta para uma compra feita em data_compra,
    de acordo com o dia_fechamento do cartão. Deve ser chamada dentro de uma
    transação já aberta (mesmo conn usado para inserir a transação da compra),
    garantindo atomicidade entre a compra e a criação da fatura.
    """
    mes_referencia = calcular_mes_referencia(cartao["dia_fechamento"], data_compra)

    fatura = (
        conn.execute(
            text(
                "SELECT * FROM faturas_cartao WHERE cartao_id = :cartao_id "
                "AND mes_referencia = :mes_referencia"
            ),
            {"cartao_id": cartao["id"], "mes_referencia": mes_referencia},
        )
        .mappings()
        .first()
    )
    if fatura is not None:
        return dict(fatura)

    data_fechamento, data_vencimento = calcular_datas_fatura(
        cartao["dia_fechamento"], cartao["dia_vencimento"], mes_referencia
    )
    resultado = conn.execute(
        text(
            """
            INSERT INTO faturas_cartao (
                cartao_id, mes_referencia, data_fechamento, data_vencimento, status
            ) VALUES (:cartao_id, :mes_referencia, :data_fechamento, :data_vencimento, 'aberta')
            RETURNING id
            """
        ),
        {
            "cartao_id": cartao["id"],
            "mes_referencia": mes_referencia,
            "data_fechamento": data_fechamento,
            "data_vencimento": data_vencimento,
        },
    )
    return _obter_fatura_conn(conn, resultado.scalar_one())


# ---------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------
def obter_fatura(id: int) -> dict | None:
    try:
        with conexao_usuario() as conn:
            linha = (
                conn.execute(text("SELECT * FROM faturas_cartao WHERE id = :id"), {"id": id})
                .mappings()
                .first()
            )
            return dict(linha) if linha is not None else None
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao obter fatura.") from exc


def listar_faturas(cartao_id: int | None = None) -> list[dict]:
    condicoes = []
    parametros: dict[str, object] = {}
    if cartao_id is not None:
        condicoes.append("cartao_id = :cartao_id")
        parametros["cartao_id"] = cartao_id
    clausula_where = f" WHERE {' AND '.join(condicoes)}" if condicoes else ""
    consulta = text(
        f"SELECT * FROM faturas_cartao{clausula_where} ORDER BY mes_referencia DESC"
    )
    try:
        with conexao_usuario() as conn:
            linhas = conn.execute(consulta, parametros).mappings().all()
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar faturas.") from exc


def calcular_total_fatura(fatura_id: int) -> Decimal:
    try:
        with conexao_usuario() as conn:
            total = conn.execute(
                text(
                    "SELECT COALESCE(SUM(valor), 0) FROM transacoes "
                    "WHERE fatura_id = :id AND tipo = 'despesa'"
                ),
                {"id": fatura_id},
            ).scalar_one()
            return total
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular total da fatura.") from exc


def calcular_total_pago(fatura_id: int) -> Decimal:
    try:
        with conexao_usuario() as conn:
            total = conn.execute(
                text(
                    "SELECT COALESCE(SUM(valor), 0) FROM pagamentos_fatura "
                    "WHERE fatura_id = :id"
                ),
                {"id": fatura_id},
            ).scalar_one()
            return total
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular total pago da fatura.") from exc


def calcular_saldo_devedor_fatura(fatura_id: int) -> Decimal:
    return calcular_total_fatura(fatura_id) - calcular_total_pago(fatura_id)


def fatura_compativel_para_pagamento(cartao_id: int, data_pagamento: date) -> dict | None:
    """Encontra a fatura mais provável para um pagamento importado: a mais
    recente já fechada até data_pagamento e que ainda tenha saldo devedor.
    Usada pela importação (Parte 12) para sugerir o vínculo de um
    "possível pagamento de fatura" — nunca cria nada, apenas sugere."""
    todas = listar_faturas(cartao_id=cartao_id)
    candidatas = [f for f in todas if f["data_fechamento"] <= data_pagamento]
    for fatura in candidatas:  # já vem ordenado por mes_referencia DESC
        if calcular_saldo_devedor_fatura(fatura["id"]) > 0:
            return fatura
    return None


def listar_pagamentos(fatura_id: int) -> list[dict]:
    try:
        with conexao_usuario() as conn:
            linhas = (
                conn.execute(
                    text(
                        "SELECT * FROM pagamentos_fatura WHERE fatura_id = :id "
                        "ORDER BY data_pagamento, id"
                    ),
                    {"id": fatura_id},
                )
                .mappings()
                .all()
            )
            return [dict(linha) for linha in linhas]
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao listar pagamentos da fatura.") from exc


def calcular_limite_utilizado(cartao_id: int) -> Decimal:
    """Soma de todas as compras no cartão ainda não pagas (saldo devedor de
    todas as faturas do cartão)."""
    try:
        with conexao_usuario() as conn:
            total_compras = conn.execute(
                text(
                    "SELECT COALESCE(SUM(valor), 0) FROM transacoes "
                    "WHERE cartao_id = :id AND tipo = 'despesa'"
                ),
                {"id": cartao_id},
            ).scalar_one()
            total_pago = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(p.valor), 0)
                    FROM pagamentos_fatura p
                    JOIN faturas_cartao f ON f.id = p.fatura_id
                    WHERE f.cartao_id = :id
                    """
                ),
                {"id": cartao_id},
            ).scalar_one()
            return total_compras - total_pago
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao calcular limite utilizado do cartão.") from exc


# ---------------------------------------------------------------------
# Pagamento de fatura (suporta pagamento parcial)
# ---------------------------------------------------------------------
def registrar_pagamento_fatura(
    fatura_id: int, conta_id: int, valor: Decimal, data_pagamento: date
) -> int:
    if not isinstance(valor, Decimal):
        raise ValueError("valor deve ser do tipo Decimal.")
    if valor <= 0:
        raise ValueError("valor do pagamento deve ser maior que zero.")
    if not isinstance(data_pagamento, date):
        raise ValueError("data_pagamento deve ser um objeto date.")

    try:
        with conexao_usuario() as conn:
            fatura = (
                conn.execute(
                    text("SELECT * FROM faturas_cartao WHERE id = :id"), {"id": fatura_id}
                )
                .mappings()
                .first()
            )
            if fatura is None:
                raise ValueError(f"Fatura {fatura_id} não encontrada.")

            conta = (
                conn.execute(text("SELECT ativa FROM contas WHERE id = :id"), {"id": conta_id})
                .mappings()
                .first()
            )
            if conta is None:
                raise ValueError(f"Conta {conta_id} não encontrada.")
            if not conta["ativa"]:
                raise ValueError(f"Conta {conta_id} está inativa.")

            total_fatura = conn.execute(
                text(
                    "SELECT COALESCE(SUM(valor), 0) FROM transacoes "
                    "WHERE fatura_id = :id AND tipo = 'despesa'"
                ),
                {"id": fatura_id},
            ).scalar_one()
            total_pago_antes = conn.execute(
                text(
                    "SELECT COALESCE(SUM(valor), 0) FROM pagamentos_fatura "
                    "WHERE fatura_id = :id"
                ),
                {"id": fatura_id},
            ).scalar_one()
            saldo_devedor = total_fatura - total_pago_antes

            if valor > saldo_devedor:
                raise ValueError(
                    f"Valor do pagamento ({valor}) maior que o saldo devedor "
                    f"da fatura ({saldo_devedor})."
                )

            resultado = conn.execute(
                text(
                    """
                    INSERT INTO pagamentos_fatura (fatura_id, conta_id, valor, data_pagamento)
                    VALUES (:fatura_id, :conta_id, :valor, :data_pagamento)
                    RETURNING id
                    """
                ),
                {
                    "fatura_id": fatura_id,
                    "conta_id": conta_id,
                    "valor": valor,
                    "data_pagamento": data_pagamento,
                },
            )
            novo_id = resultado.scalar_one()

            total_pago_depois = total_pago_antes + valor
            novo_status = "paga" if total_pago_depois >= total_fatura else "parcial"
            conn.execute(
                text(
                    "UPDATE faturas_cartao SET status = :status, atualizado_em = now() "
                    "WHERE id = :id"
                ),
                {"status": novo_status, "id": fatura_id},
            )

            return novo_id
    except SQLAlchemyError as exc:
        raise ErroBancoDeDados("Falha ao registrar pagamento da fatura.") from exc
