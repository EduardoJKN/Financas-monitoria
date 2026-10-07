"""Direção de transferências reclassificadas na importação (correção):
a conta do extrato não é sempre a origem — depende de a linha original ser
receita (entrada) ou despesa (saída). Testa o efeito real no saldo das duas
contas, exatamente como a página de Importação monta a transação (via
importador.resolver_contas_transferencia + transacoes.criar_transacao)."""

from datetime import date
from decimal import Decimal

from src import contas, importador, resumo_financeiro as resumo, transacoes


def test_transferencia_enviada_debita_conta_do_extrato_credita_outra(conta_a, conta_b):
    """Linha original de DESPESA ("Pix enviado") reclassificada como
    transferência: a conta do extrato (conta_a) é a origem."""
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("1000.00"))
    contas.atualizar_conta(conta_b, saldo_inicial=Decimal("0.00"))

    conta_origem_id, conta_destino_id = importador.resolver_contas_transferencia(
        "despesa", conta_extrato_id=conta_a, outra_conta_id=conta_b
    )
    tid = transacoes.criar_transacao(
        tipo="transferencia",
        descricao="Pix enviado",
        valor=Decimal("200.00"),
        data_transacao=date(2026, 10, 5),
        conta_id=conta_origem_id,
        conta_destino_id=conta_destino_id,
        origem="importacao",
    )
    try:
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("800.00")  # debitada
        assert resumo.calcular_saldo_conta(conta_b) == Decimal("200.00")  # creditada
    finally:
        transacoes.excluir_transacao(tid)


def test_transferencia_recebida_credita_conta_do_extrato_debita_outra(conta_a, conta_b):
    """Linha original de RECEITA ("Pix recebido") reclassificada como
    transferência: a conta do extrato (conta_a) é o DESTINO, não a origem —
    o dinheiro vem da outra conta (conta_b)."""
    contas.atualizar_conta(conta_a, saldo_inicial=Decimal("0.00"))
    contas.atualizar_conta(conta_b, saldo_inicial=Decimal("1000.00"))

    conta_origem_id, conta_destino_id = importador.resolver_contas_transferencia(
        "receita", conta_extrato_id=conta_a, outra_conta_id=conta_b
    )
    tid = transacoes.criar_transacao(
        tipo="transferencia",
        descricao="Pix recebido",
        valor=Decimal("200.00"),
        data_transacao=date(2026, 10, 5),
        conta_id=conta_origem_id,
        conta_destino_id=conta_destino_id,
        origem="importacao",
    )
    try:
        # a conta do extrato (conta_a) recebeu — saldo sobe, não desce
        assert resumo.calcular_saldo_conta(conta_a) == Decimal("200.00")
        assert resumo.calcular_saldo_conta(conta_b) == Decimal("800.00")
    finally:
        transacoes.excluir_transacao(tid)
