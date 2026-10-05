import pytest

from src import categorias


def test_criar_categoria_principal():
    categoria_id = categorias.criar_categoria("Alimentação Pytest", "despesa")
    try:
        categoria = categorias.obter_categoria(categoria_id)
        assert categoria is not None
        assert categoria["categoria_pai_id"] is None
    finally:
        categorias.excluir_categoria(categoria_id)


def test_criar_subcategoria():
    pai_id = categorias.criar_categoria("Alimentação Pytest Pai", "despesa")
    try:
        filha_id = categorias.criar_categoria(
            "Delivery Pytest", "despesa", categoria_pai_id=pai_id
        )
        try:
            filha = categorias.obter_categoria(filha_id)
            assert filha["categoria_pai_id"] == pai_id
        finally:
            categorias.excluir_categoria(filha_id)
    finally:
        categorias.excluir_categoria(pai_id)


def test_editar_e_desativar_categoria():
    categoria_id = categorias.criar_categoria("Categoria Pytest Editar", "ambos")
    try:
        categorias.atualizar_categoria(categoria_id, nome="Categoria Pytest Editada")
        categoria = categorias.obter_categoria(categoria_id)
        assert categoria["nome"] == "Categoria Pytest Editada"

        categorias.atualizar_categoria(categoria_id, ativa=False)
        categoria = categorias.obter_categoria(categoria_id)
        assert categoria["ativa"] is False
    finally:
        categorias.excluir_categoria(categoria_id)


def test_excluir_categoria_sem_dependencias():
    categoria_id = categorias.criar_categoria("Categoria Pytest Excluir", "despesa")
    categorias.excluir_categoria(categoria_id)
    assert categorias.obter_categoria(categoria_id) is None


def test_erro_hierarquia_tipo_incompativel():
    pai_id = categorias.criar_categoria("Receita Pytest Pai", "receita")
    try:
        with pytest.raises(ValueError):
            categorias.criar_categoria("Filha Incompatível", "despesa", categoria_pai_id=pai_id)
    finally:
        categorias.excluir_categoria(pai_id)


def test_erro_hierarquia_pai_inativo():
    pai_id = categorias.criar_categoria("Pai Inativo Pytest", "ambos")
    try:
        categorias.atualizar_categoria(pai_id, ativa=False)
        with pytest.raises(ValueError):
            categorias.criar_categoria("Filha de Pai Inativo", "despesa", categoria_pai_id=pai_id)
    finally:
        categorias.atualizar_categoria(pai_id, ativa=True)
        categorias.excluir_categoria(pai_id)


def test_erro_categoria_nao_pode_ser_pai_dela_mesma():
    categoria_id = categorias.criar_categoria("Auto Referência Pytest", "despesa")
    try:
        with pytest.raises(ValueError):
            categorias.atualizar_categoria(categoria_id, categoria_pai_id=categoria_id)
    finally:
        categorias.excluir_categoria(categoria_id)


def test_categoria_ambos_aceita_filha_receita_e_despesa():
    pai_id = categorias.criar_categoria("Ambos Pytest Pai", "ambos")
    try:
        filha_receita_id = categorias.criar_categoria(
            "Filha Receita", "receita", categoria_pai_id=pai_id
        )
        filha_despesa_id = categorias.criar_categoria(
            "Filha Despesa", "despesa", categoria_pai_id=pai_id
        )
        categorias.excluir_categoria(filha_receita_id)
        categorias.excluir_categoria(filha_despesa_id)
    finally:
        categorias.excluir_categoria(pai_id)
