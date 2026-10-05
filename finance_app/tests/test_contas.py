from decimal import Decimal

import pytest

from src import contas


def test_criar_obter_conta():
    conta_id = contas.criar_conta("Conta Pytest CRUD", "conta_corrente", "Banco X", Decimal("100"))
    try:
        conta = contas.obter_conta(conta_id)
        assert conta is not None
        assert conta["nome"] == "Conta Pytest CRUD"
        assert conta["saldo_inicial"] == Decimal("100")
        assert conta["ativa"] is True
    finally:
        contas.excluir_conta(conta_id)


def test_listar_contas_inclui_criada():
    conta_id = contas.criar_conta("Conta Pytest Listagem", "poupanca", None, Decimal("0"))
    try:
        todas = contas.listar_contas(incluir_inativas=True)
        assert any(c["id"] == conta_id for c in todas)
    finally:
        contas.excluir_conta(conta_id)


def test_atualizar_conta():
    conta_id = contas.criar_conta("Conta Pytest Editar", "conta_corrente", None, Decimal("0"))
    try:
        contas.atualizar_conta(conta_id, nome="Conta Pytest Editada", instituicao="Novo Banco")
        conta = contas.obter_conta(conta_id)
        assert conta["nome"] == "Conta Pytest Editada"
        assert conta["instituicao"] == "Novo Banco"
    finally:
        contas.excluir_conta(conta_id)


def test_desativar_conta():
    conta_id = contas.criar_conta("Conta Pytest Desativar", "conta_corrente", None, Decimal("0"))
    try:
        contas.atualizar_conta(conta_id, ativa=False)
        conta = contas.obter_conta(conta_id)
        assert conta["ativa"] is False
    finally:
        contas.excluir_conta(conta_id)


def test_excluir_conta_sem_transacoes_remove_de_vez():
    conta_id = contas.criar_conta("Conta Pytest Excluir", "conta_corrente", None, Decimal("0"))
    contas.excluir_conta(conta_id)
    assert contas.obter_conta(conta_id) is None


def test_criar_conta_tipo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        contas.criar_conta("Conta Inválida", "tipo_invalido", None, Decimal("0"))


def test_criar_conta_saldo_inicial_nao_decimal_levanta_erro():
    with pytest.raises(ValueError):
        contas.criar_conta("Conta Inválida", "conta_corrente", None, 100)


def test_criar_conta_nome_vazio_levanta_erro():
    with pytest.raises(ValueError):
        contas.criar_conta("", "conta_corrente", None, Decimal("0"))
