from datetime import date
from decimal import Decimal

from src import faturas, resumo_financeiro as resumo, transacoes
from src.banco_de_dados import conexao_usuario


def test_saldo_considera_receita_despesa_transferencia(conta_a, conta_b, categoria_despesa, categoria_receita):
    ids = []
    try:
        ids.append(
            transacoes.criar_transacao(
                tipo="receita", descricao="Salário Pytest", valor=Decimal("3000"),
                data_transacao=date(2026, 3, 1), conta_id=conta_a, categoria_id=categoria_receita,
            )
        )
        ids.append(
            transacoes.criar_transacao(
                tipo="despesa", descricao="Mercado Pytest", valor=Decimal("500"),
                data_transacao=date(2026, 3, 2), conta_id=conta_a, categoria_id=categoria_despesa,
            )
        )
        ids.append(
            transacoes.criar_transacao(
                tipo="transferencia", descricao="Transferência Pytest", valor=Decimal("1000"),
                data_transacao=date(2026, 3, 3), conta_id=conta_a, conta_destino_id=conta_b,
            )
        )

        saldo_a = resumo.calcular_saldo_conta(conta_a)
        saldo_b = resumo.calcular_saldo_conta(conta_b)
        assert saldo_a == Decimal("1500.00")  # 0 + 3000 - 500 - 1000
        assert saldo_b == Decimal("1000.00")  # 0 + 1000

        resultado_periodo = resumo.calcular_resumo_periodo(date(2026, 3, 1), date(2026, 3, 31))
        assert resultado_periodo["resultado"] == Decimal("2500.00")  # transferência não conta
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


def test_compra_no_cartao_nao_reduz_saldo_bancario_ate_pagamento(
    conta_a, cartao_a, categoria_despesa
):
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao="Compra Cartão Pytest", valor=Decimal("600"),
        data_transacao=date(2026, 3, 10), cartao_id=cartao_a, categoria_id=categoria_despesa,
    )
    try:
        t = transacoes.obter_transacao(tid)
        fatura_id = t["fatura_id"]

        assert resumo.calcular_saldo_conta(conta_a) == Decimal("0")  # saldo inicial, sem redução

        resultado_periodo = resumo.calcular_resumo_periodo(date(2026, 3, 1), date(2026, 3, 31))
        assert resultado_periodo["total_despesas"] == Decimal("600.00")  # conta como despesa na compra

        faturas.registrar_pagamento_fatura(fatura_id, conta_a, Decimal("600"), date(2026, 3, 27))

        assert resumo.calcular_saldo_conta(conta_a) == Decimal("-600.00")  # agora reduz o saldo

        resultado_periodo_depois = resumo.calcular_resumo_periodo(date(2026, 3, 1), date(2026, 3, 31))
        assert resultado_periodo_depois["total_despesas"] == Decimal("600.00")  # NÃO duplica
    finally:
        transacoes.excluir_transacao(tid)
        with conexao_usuario() as conn:
            from sqlalchemy import text

            conn.execute(text("DELETE FROM pagamentos_fatura WHERE conta_id = :id"), {"id": conta_a})
            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a})


def test_calcular_intervalo_periodo_este_mes():
    inicio, fim = resumo.calcular_intervalo_periodo("este_mes", hoje=date(2026, 3, 15))
    assert inicio == date(2026, 3, 1)
    assert fim == date(2026, 3, 15)


def test_calcular_intervalo_periodo_invalido_levanta_erro():
    import pytest

    with pytest.raises(ValueError):
        resumo.calcular_intervalo_periodo("periodo_invalido")
