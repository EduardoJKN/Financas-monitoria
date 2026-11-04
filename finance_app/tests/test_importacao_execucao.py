"""Testes de src/importacao_execucao.py — função compartilhada entre a
página Streamlit de Importação e o backend FastAPI para confirmar uma
linha já classificada (normal / transferência / pagamento de fatura)."""

from datetime import date
from decimal import Decimal

import pytest

from src import contas, importacao_execucao, resumo_financeiro as resumo, transacoes


def test_confirmar_linha_normal_cria_transacao_comum(conta_a, categoria_despesa):
    resultado = importacao_execucao.confirmar_linha(
        classificacao="normal",
        tipo="despesa",
        descricao="Supermercado",
        valor=Decimal("150.00"),
        data_transacao=date(2026, 10, 1),
        conta_id_importacao=conta_a,
        categoria_id=categoria_despesa,
    )
    try:
        assert resultado["tipo_resultado"] == "transacao"
        criada = transacoes.obter_transacao(resultado["transacao_id"])
        assert criada["tipo"] == "despesa"
        assert criada["categoria_id"] == categoria_despesa
    finally:
        transacoes.excluir_transacao(resultado["transacao_id"])


def test_confirmar_linha_transferencia_respeita_direcao_despesa(conta_a, conta_b):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    contas.atualizar_conta(conta_b, saldo_inicial=Decimal("0.00"))

    resultado = importacao_execucao.confirmar_linha(
        classificacao="transferencia",
        tipo="despesa",
        descricao="Pix enviado",
        valor=Decimal("300.00"),
        data_transacao=date(2026, 10, 5),
        conta_id_importacao=conta_a,
        outra_conta_id=conta_b,
    )
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("700.00")
        assert resumo.calcular_saldo_conta(conta_b) == Decimal("300.00")
    finally:
        transacoes.excluir_transacao(resultado["transacao_id"])


def test_confirmar_linha_transferencia_respeita_direcao_receita(conta_a, conta_b):
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("0.00"))
    contas.atualizar_conta(conta_b, saldo_inicial=Decimal("1000.00"))

    resultado = importacao_execucao.confirmar_linha(
        classificacao="transferencia",
        tipo="receita",
        descricao="Pix recebido",
        valor=Decimal("300.00"),
        data_transacao=date(2026, 10, 5),
        conta_id_importacao=conta_a,
        outra_conta_id=conta_b,
    )
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("300.00")
        assert resumo.calcular_saldo_conta(conta_b) == Decimal("700.00")
    finally:
        transacoes.excluir_transacao(resultado["transacao_id"])


def test_confirmar_linha_transferencia_sem_outra_conta_levanta_erro(conta_a):
    with pytest.raises(importacao_execucao.ErroImportacao):
        importacao_execucao.confirmar_linha(
            classificacao="transferencia",
            tipo="despesa",
            descricao="Pix enviado",
            valor=Decimal("100.00"),
            data_transacao=date(2026, 10, 5),
            conta_id_importacao=conta_a,
            outra_conta_id=None,
        )


def test_confirmar_linha_pagamento_fatura_sem_fatura_compativel_nunca_cria_despesa(
    conta_a, cartao_a
):
    antes = transacoes.listar_transacoes(conta_id=conta_a)
    with pytest.raises(importacao_execucao.ErroImportacao):
        importacao_execucao.confirmar_linha(
            classificacao="pagamento_fatura",
            tipo="despesa",
            descricao="Pagamento de fatura",
            valor=Decimal("500.00"),
            data_transacao=date(2026, 10, 5),
            conta_id_importacao=conta_a,
            cartao_vinculado_id=cartao_a,
        )
    depois = transacoes.listar_transacoes(conta_id=conta_a)
    # nenhuma transação foi criada (nem despesa comum, nem nada) — a
    # ausência de fatura compatível nunca degrada silenciosamente
    assert len(antes) == len(depois)


def test_confirmar_linha_pagamento_fatura_com_fatura_compativel_nao_duplica_despesa(
    conta_a, cartao_a, categoria_despesa
):
    tid_compra = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Compra no cartao",
        valor=Decimal("400.00"),
        data_transacao=date(2026, 10, 1),
        cartao_id=cartao_a,
        categoria_id=categoria_despesa,
    )
    try:
        # cartao_a fecha dia 25; o pagamento precisa ser em/após o
        # fechamento da fatura que contém a compra (01/10) para ser
        # considerado compatível.
        resultado = importacao_execucao.confirmar_linha(
            classificacao="pagamento_fatura",
            tipo="despesa",
            descricao="Pagamento de fatura",
            valor=Decimal("400.00"),
            data_transacao=date(2026, 10, 26),
            conta_id_importacao=conta_a,
            cartao_vinculado_id=cartao_a,
        )
        assert resultado["tipo_resultado"] == "pagamento_fatura"
        # o pagamento NÃO cria uma segunda transação de despesa na conta —
        # a única despesa é a compra original no cartão
        despesas_conta = [
            t for t in transacoes.listar_transacoes(conta_id=conta_a) if t["tipo"] == "despesa"
        ]
        assert despesas_conta == []
    finally:
        transacoes.excluir_transacao(tid_compra)
        from sqlalchemy import text

        from src.banco_de_dados import conexao_usuario

        with conexao_usuario() as conn:
            conn.execute(text("DELETE FROM pagamentos_fatura WHERE conta_id = :id"), {"id": conta_a})
            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a})


def test_confirmar_linha_classificacao_invalida_levanta_erro(conta_a):
    with pytest.raises(importacao_execucao.ErroImportacao):
        importacao_execucao.confirmar_linha(
            classificacao="algo_invalido",
            tipo="despesa",
            descricao="X",
            valor=Decimal("10.00"),
            data_transacao=date(2026, 10, 5),
            conta_id_importacao=conta_a,
        )
