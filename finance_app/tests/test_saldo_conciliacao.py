"""Testes da conciliação de saldo com data de referência (Parte 28).

saldo_inicial = saldo da conta ao final de data_saldo_inicial. Movimentações
até essa data não devem ser somadas de novo; só as posteriores.
"""

from datetime import date
from decimal import Decimal

from src import contas, resumo_financeiro as resumo, transacoes
from src.banco_de_dados import ErroBancoDeDados


def _despesa(conta_id, categoria_id, valor, data_transacao):
    return transacoes.criar_transacao(
        tipo="despesa",
        descricao="Despesa conciliacao",
        valor=Decimal(str(valor)),
        data_transacao=data_transacao,
        conta_id=conta_id,
        categoria_id=categoria_id,
        origem="manual",
    )


def _receita(conta_id, categoria_id, valor, data_transacao):
    return transacoes.criar_transacao(
        tipo="receita",
        descricao="Receita conciliacao",
        valor=Decimal(str(valor)),
        data_transacao=data_transacao,
        conta_id=conta_id,
        categoria_id=categoria_id,
        origem="manual",
    )


# ---------------------------------------------------------------------
# Conta sem data de referência: compatibilidade com comportamento antigo
# ---------------------------------------------------------------------
def test_conta_sem_data_referencia_soma_toda_movimentacao(conta_a, categoria_despesa):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    tid = _despesa(conta_a, categoria_despesa, "200.00", date(2020, 1, 1))
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("800.00")
        assert resumo.precisa_conciliacao(conta_a) is True
    finally:
        transacoes.excluir_transacao(tid)


# ---------------------------------------------------------------------
# Conta com data de referência: movimentações até a data não duplicam
# ---------------------------------------------------------------------
def test_transacao_anterior_a_referencia_nao_e_somada_de_novo(conta_a, categoria_despesa):
    contas.atualizar_conta(
        conta_a, saldo_inicial=Decimal("1000.00"), data_saldo_inicial=date(2026, 1, 15)
    )
    tid = _despesa(conta_a, categoria_despesa, "300.00", date(2026, 1, 10))
    try:
        # a despesa de 10/01 já está contemplada no saldo de referência (15/01)
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("1000.00")
    finally:
        transacoes.excluir_transacao(tid)


def test_transacao_na_propria_data_referencia_nao_e_somada_de_novo(conta_a, categoria_despesa):
    contas.atualizar_conta(
        conta_a, saldo_inicial=Decimal("1000.00"), data_saldo_inicial=date(2026, 1, 15)
    )
    tid = _despesa(conta_a, categoria_despesa, "300.00", date(2026, 1, 15))
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("1000.00")
    finally:
        transacoes.excluir_transacao(tid)


def test_transacao_posterior_a_referencia_e_somada(conta_a, categoria_despesa, categoria_receita):
    contas.atualizar_conta(
        conta_a, saldo_inicial=Decimal("1000.00"), data_saldo_inicial=date(2026, 1, 15)
    )
    tid1 = _despesa(conta_a, categoria_despesa, "100.00", date(2026, 1, 10))  # antes: ignorada
    tid2 = _receita(conta_a, categoria_receita, "500.00", date(2026, 1, 20))  # depois: somada
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("1500.00")
    finally:
        transacoes.excluir_transacao(tid1)
        transacoes.excluir_transacao(tid2)


def test_transferencia_posterior_a_referencia_afeta_ambas_contas(conta_a, conta_b):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"), data_saldo_inicial=date(2026, 1, 15))
    contas.atualizar_conta(conta_b, saldo_inicial=Decimal("0.00"), data_saldo_inicial=date(2026, 1, 15))
    tid = transacoes.criar_transacao(
        tipo="transferencia",
        descricao="Transferencia conciliacao",
        valor=Decimal("200.00"),
        data_transacao=date(2026, 1, 20),
        conta_id=conta_a,
        conta_destino_id=conta_b,
        origem="manual",
    )
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("800.00")
        assert resumo.calcular_saldo_conta(conta_b) == Decimal("200.00")
    finally:
        transacoes.excluir_transacao(tid)


def test_pagamento_fatura_posterior_a_referencia_reduz_saldo(conta_a, cartao_a, categoria_despesa):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"), data_saldo_inicial=date(2026, 1, 15))
    tid_compra = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Compra no cartao",
        valor=Decimal("300.00"),
        data_transacao=date(2026, 1, 20),
        cartao_id=cartao_a,
        categoria_id=categoria_despesa,
        origem="manual",
    )
    try:
        compra = transacoes.obter_transacao(tid_compra)
        from src import faturas

        faturas.registrar_pagamento_fatura(
            compra["fatura_id"], conta_a, Decimal("300.00"), date(2026, 1, 25)
        )
        # a compra no cartão não afeta o saldo bancário; só o pagamento da fatura
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("700.00")
    finally:
        transacoes.excluir_transacao(tid_compra)
        from src import faturas as faturas_cleanup
        from src.banco_de_dados import conexao_usuario
        from sqlalchemy import text

        with conexao_usuario() as conn:
            conn.execute(text("DELETE FROM pagamentos_fatura WHERE conta_id = :id"), {"id": conta_a})
            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a})


# ---------------------------------------------------------------------
# Assistente de conciliação explícito (Parte 10)
# ---------------------------------------------------------------------
def test_pre_visualizar_conciliacao_mostra_diferenca(conta_a, categoria_despesa):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    tid = _despesa(conta_a, categoria_despesa, "100.00", date(2020, 1, 1))
    try:
        previa = resumo.pre_visualizar_conciliacao(conta_a, date(2026, 1, 1), Decimal("950.00"))
        assert previa["saldo_calculado_atual"] == Decimal("900.00")
        assert previa["diferenca"] == Decimal("50.00")
    finally:
        transacoes.excluir_transacao(tid)


def test_conciliar_conta_faz_saldo_bater_exatamente(conta_a, categoria_despesa):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    tid = _despesa(conta_a, categoria_despesa, "100.00", date(2020, 1, 1))
    try:
        resultado = resumo.conciliar_conta(conta_a, date(2026, 1, 1), Decimal("3768.01"))
        assert resultado["saldo_atual"] == Decimal("3768.01")
        assert resumo.precisa_conciliacao(conta_a) is False
    finally:
        transacoes.excluir_transacao(tid)


def test_conciliar_conta_nunca_cria_lancamento(conta_a):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    antes = transacoes.listar_transacoes(conta_id=conta_a)
    resumo.conciliar_conta(conta_a, date(2026, 1, 1), Decimal("1500.00"))
    depois = transacoes.listar_transacoes(conta_id=conta_a)
    assert len(antes) == len(depois)


def test_precisa_conciliacao_conta_inexistente_levanta_erro():
    import pytest

    with pytest.raises(ValueError):
        resumo.precisa_conciliacao(999999999)
