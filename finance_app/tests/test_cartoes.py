from decimal import Decimal

import pytest

from src import cartoes


def test_criar_obter_cartao(conta_a):
    cartao_id = cartoes.criar_cartao(
        "Cartão Pytest", Decimal("5000"), dia_fechamento=10, dia_vencimento=20,
        conta_pagamento_id=conta_a,
    )
    try:
        cartao = cartoes.obter_cartao(cartao_id)
        assert cartao["nome"] == "Cartão Pytest"
        assert cartao["limite"] == Decimal("5000")
        assert cartao["ativo"] is True
    finally:
        cartoes.excluir_cartao(cartao_id)


def test_atualizar_e_desativar_cartao(conta_a):
    cartao_id = cartoes.criar_cartao("Cartão Pytest Editar", Decimal("1000"), 5, 15)
    try:
        cartoes.atualizar_cartao(cartao_id, nome="Cartão Pytest Editado", limite=Decimal("2000"))
        cartao = cartoes.obter_cartao(cartao_id)
        assert cartao["nome"] == "Cartão Pytest Editado"
        assert cartao["limite"] == Decimal("2000")

        cartoes.atualizar_cartao(cartao_id, ativo=False)
        cartao = cartoes.obter_cartao(cartao_id)
        assert cartao["ativo"] is False
    finally:
        cartoes.excluir_cartao(cartao_id)


def test_limite_negativo_levanta_erro():
    with pytest.raises(ValueError):
        cartoes.criar_cartao("Cartão Inválido", Decimal("-1"), 5, 15)


@pytest.mark.parametrize("dia", [0, 32, -1])
def test_dia_fechamento_invalido_levanta_erro(dia):
    with pytest.raises(ValueError):
        cartoes.criar_cartao("Cartão Inválido", Decimal("1000"), dia, 15)


@pytest.mark.parametrize("dia", [0, 32])
def test_dia_vencimento_invalido_levanta_erro(dia):
    with pytest.raises(ValueError):
        cartoes.criar_cartao("Cartão Inválido", Decimal("1000"), 5, dia)


def test_conta_pagamento_inexistente_levanta_erro():
    with pytest.raises(ValueError):
        cartoes.criar_cartao("Cartão Inválido", Decimal("1000"), 5, 15, conta_pagamento_id=999999999)
