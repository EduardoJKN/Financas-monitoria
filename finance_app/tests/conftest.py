"""Fixtures compartilhadas. Testes que tocam o banco de dados criam seus
próprios dados e os removem ao final (fixtures com yield + teardown, ou
try/finally dentro do teste) — nenhum dado de teste deve sobreviver à
execução da suíte.
"""

from decimal import Decimal

import pytest

from src import cartoes, categorias, contas


@pytest.fixture
def conta_a():
    conta_id = contas.criar_conta("Conta Teste A Pytest", "conta_corrente", None, Decimal("0"))
    yield conta_id
    contas.excluir_conta(conta_id)


@pytest.fixture
def conta_b():
    conta_id = contas.criar_conta("Conta Teste B Pytest", "poupanca", None, Decimal("0"))
    yield conta_id
    contas.excluir_conta(conta_id)


@pytest.fixture
def categoria_despesa():
    categoria_id = categorias.criar_categoria("Despesa Teste Pytest", "despesa")
    yield categoria_id
    categorias.excluir_categoria(categoria_id)


@pytest.fixture
def categoria_receita():
    categoria_id = categorias.criar_categoria("Receita Teste Pytest", "receita")
    yield categoria_id
    categorias.excluir_categoria(categoria_id)


@pytest.fixture
def cartao_a(conta_a):
    cartao_id = cartoes.criar_cartao(
        "Cartão Teste Pytest",
        Decimal("5000"),
        dia_fechamento=25,
        dia_vencimento=5,
        conta_pagamento_id=conta_a,
    )
    yield cartao_id
    cartoes.excluir_cartao(cartao_id)
