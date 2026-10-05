from datetime import date
from decimal import Decimal

import pytest

from src import cartoes, faturas, transacoes
from src.banco_de_dados import obter_engine


# ---------------------------------------------------------------------
# Regra de fechamento (lógica pura, sem banco)
# ---------------------------------------------------------------------
def test_compra_antes_do_fechamento_fica_na_fatura_do_mes_da_compra():
    mes_ref = faturas.calcular_mes_referencia(dia_fechamento=25, data_compra=date(2026, 3, 20))
    assert mes_ref == date(2026, 3, 1)


def test_compra_no_dia_do_fechamento_ainda_entra_na_fatura_que_fecha():
    mes_ref = faturas.calcular_mes_referencia(dia_fechamento=25, data_compra=date(2026, 3, 25))
    assert mes_ref == date(2026, 3, 1)


def test_compra_depois_do_fechamento_vai_para_proxima_fatura():
    mes_ref = faturas.calcular_mes_referencia(dia_fechamento=25, data_compra=date(2026, 3, 26))
    assert mes_ref == date(2026, 4, 1)


def test_mudanca_de_mes_e_virada_de_ano():
    mes_ref = faturas.calcular_mes_referencia(dia_fechamento=25, data_compra=date(2026, 12, 26))
    assert mes_ref == date(2027, 1, 1)


def test_fevereiro_com_dia_fechamento_alto_clampado():
    mes_ref = faturas.calcular_mes_referencia(dia_fechamento=30, data_compra=date(2026, 2, 28))
    assert mes_ref == date(2026, 2, 1)


def test_calcular_datas_fatura_vencimento_mes_seguinte():
    data_fechamento, data_vencimento = faturas.calcular_datas_fatura(25, 5, date(2026, 3, 1))
    assert data_fechamento == date(2026, 3, 25)
    assert data_vencimento == date(2026, 4, 5)


def test_calcular_datas_fatura_vencimento_mesmo_mes():
    data_fechamento, data_vencimento = faturas.calcular_datas_fatura(1, 10, date(2026, 3, 1))
    assert data_fechamento == date(2026, 3, 1)
    assert data_vencimento == date(2026, 3, 10)


def test_calcular_datas_fatura_fechamento_clampado_em_fevereiro():
    data_fechamento, _ = faturas.calcular_datas_fatura(31, 10, date(2026, 2, 1))
    assert data_fechamento == date(2026, 2, 28)


def test_calcular_datas_fatura_virada_de_ano_no_vencimento():
    data_fechamento, data_vencimento = faturas.calcular_datas_fatura(25, 5, date(2026, 12, 1))
    assert data_fechamento == date(2026, 12, 25)
    assert data_vencimento == date(2027, 1, 5)


# ---------------------------------------------------------------------
# Resolução de fatura (precisa de conexão) + pagamentos (precisa de banco)
# ---------------------------------------------------------------------
def test_obter_ou_criar_fatura_e_idempotente(cartao_a):
    cartao = cartoes.obter_cartao(cartao_a)
    try:
        with obter_engine().begin() as conn:
            fatura1 = faturas.obter_ou_criar_fatura(conn, cartao, date(2026, 3, 10))
            fatura2 = faturas.obter_ou_criar_fatura(conn, cartao, date(2026, 3, 15))
        assert fatura1["id"] == fatura2["id"]  # mesma fatura, não cria duplicada
    finally:
        with obter_engine().begin() as conn:
            from sqlalchemy import text

            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a})


def test_pagamento_integral_e_parcial(conta_a, cartao_a, categoria_despesa):
    tid = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Compra Fatura Pytest",
        valor=Decimal("300"),
        data_transacao=date(2026, 3, 10),
        cartao_id=cartao_a,
        categoria_id=categoria_despesa,
    )
    try:
        t = transacoes.obter_transacao(tid)
        fatura_id = t["fatura_id"]

        # pagamento parcial
        faturas.registrar_pagamento_fatura(fatura_id, conta_a, Decimal("100"), date(2026, 3, 26))
        fatura = faturas.obter_fatura(fatura_id)
        assert fatura["status"] == "parcial"
        assert faturas.calcular_saldo_devedor_fatura(fatura_id) == Decimal("200")

        # pagamento do restante -> fatura paga
        faturas.registrar_pagamento_fatura(fatura_id, conta_a, Decimal("200"), date(2026, 3, 27))
        fatura = faturas.obter_fatura(fatura_id)
        assert fatura["status"] == "paga"
        assert faturas.calcular_saldo_devedor_fatura(fatura_id) == Decimal("0")

        # pagamento excedente deve falhar
        with pytest.raises(ValueError):
            faturas.registrar_pagamento_fatura(fatura_id, conta_a, Decimal("1"), date(2026, 3, 28))
    finally:
        transacoes.excluir_transacao(tid)
        with obter_engine().begin() as conn:
            from sqlalchemy import text

            conn.execute(text("DELETE FROM pagamentos_fatura WHERE conta_id = :id"), {"id": conta_a})
            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a})
