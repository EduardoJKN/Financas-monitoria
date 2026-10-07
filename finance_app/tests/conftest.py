"""Fixtures compartilhadas. Testes que tocam o banco de dados criam seus
próprios dados e os removem ao final (fixtures com yield + teardown, ou
try/finally dentro do teste) — nenhum dado de teste deve sobreviver à
execução da suíte.

Isolamento multiusuário: todo acesso a dados (via conexao_usuario()) exige
um usuário autenticado no contexto atual (ver src/banco_de_dados.py). A
fixture `_usuario_padrao`, autouse, define esse contexto para um UUID fixo
de teste antes de cada teste e limpa depois — assim os ~150 testes
existentes continuam funcionando sem precisar saber nada sobre usuario_id,
e ainda exercitam o caminho real (RLS pela role app_runtime), não um atalho
administrativo. As fixtures `usuario_a_id`/`usuario_b_id` existem para os
testes que precisam verificar isolamento entre dois usuários distintos.
"""

import uuid
from decimal import Decimal

import pytest

from src import cartoes, categorias, contas
from src.banco_de_dados import definir_usuario_atual

USUARIO_TESTE_PADRAO = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _usuario_padrao():
    definir_usuario_atual(USUARIO_TESTE_PADRAO)
    yield
    definir_usuario_atual(None)


@pytest.fixture
def usuario_a_id():
    return str(uuid.uuid4())


@pytest.fixture
def usuario_b_id():
    return str(uuid.uuid4())


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
