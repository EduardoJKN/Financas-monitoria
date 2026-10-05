import pytest

from src import categorias, categorizador


def test_criar_regra_texto_vazio_levanta_erro(categoria_despesa):
    with pytest.raises(ValueError):
        categorizador.criar_regra("", "contem", categoria_despesa)


def test_criar_regra_operador_invalido_levanta_erro(categoria_despesa):
    with pytest.raises(ValueError):
        categorizador.criar_regra("TESTE", "operador_invalido", categoria_despesa)


def test_criar_regra_prioridade_nao_inteira_levanta_erro(categoria_despesa):
    with pytest.raises(ValueError):
        categorizador.criar_regra("TESTE", "contem", categoria_despesa, prioridade=1.5)


def test_criar_regra_categoria_inexistente_levanta_erro():
    with pytest.raises(ValueError):
        categorizador.criar_regra("TESTE", "contem", 999999999)


def test_criar_regra_categoria_inativa_levanta_erro(categoria_despesa):
    categorias.atualizar_categoria(categoria_despesa, ativa=False)
    try:
        with pytest.raises(ValueError):
            categorizador.criar_regra("TESTE", "contem", categoria_despesa)
    finally:
        categorias.atualizar_categoria(categoria_despesa, ativa=True)


def test_operador_contem(categoria_despesa):
    regra_id = categorizador.criar_regra("IFOOD", "contem", categoria_despesa, prioridade=10)
    try:
        assert categorizador.categorizar_descricao("IFOOD *DELIVERY", "despesa") == categoria_despesa
    finally:
        categorizador.excluir_regra(regra_id)


def test_operador_comeca_com(categoria_despesa):
    regra_id = categorizador.criar_regra("UBER", "comeca_com", categoria_despesa, prioridade=10)
    try:
        assert categorizador.categorizar_descricao("UBER TRIP", "despesa") == categoria_despesa
        assert categorizador.categorizar_descricao("MEU UBER PASSEIO", "despesa") is None
    finally:
        categorizador.excluir_regra(regra_id)


def test_operador_igual(categoria_receita):
    regra_id = categorizador.criar_regra("SALARIO", "igual", categoria_receita, prioridade=10)
    try:
        assert categorizador.categorizar_descricao("Salario", "receita") == categoria_receita
        assert categorizador.categorizar_descricao("Salario Outubro", "receita") is None
    finally:
        categorizador.excluir_regra(regra_id)


def test_prioridade_entre_duas_regras_que_casam(categoria_despesa, categoria_receita):
    # usa duas categorias de despesa distintas via fixtures extras ad-hoc
    outra_categoria_id = categorias.criar_categoria("Mercado B Pytest", "despesa")
    try:
        regra_baixa = categorizador.criar_regra("MERCADO", "contem", categoria_despesa, prioridade=1)
        regra_alta = categorizador.criar_regra("MERCADO", "contem", outra_categoria_id, prioridade=10)
        try:
            resultado = categorizador.categorizar_descricao("Compra Mercado Central", "despesa")
            assert resultado == outra_categoria_id  # maior prioridade vence
        finally:
            categorizador.excluir_regra(regra_baixa)
            categorizador.excluir_regra(regra_alta)
    finally:
        categorias.excluir_categoria(outra_categoria_id)


def test_categoria_incompativel_com_tipo_nao_e_aplicada(categoria_receita):
    regra_id = categorizador.criar_regra("SALARIO", "igual", categoria_receita, prioridade=10)
    try:
        # categoria é de receita; buscando para despesa não deve retornar nada
        assert categorizador.categorizar_descricao("Salario", "despesa") is None
    finally:
        categorizador.excluir_regra(regra_id)


def test_regra_inativa_e_ignorada(categoria_despesa):
    regra_id = categorizador.criar_regra("NETFLIX", "contem", categoria_despesa, prioridade=10)
    try:
        categorizador.atualizar_regra(regra_id, ativa=False)
        assert categorizador.categorizar_descricao("NETFLIX ASSINATURA", "despesa") is None
    finally:
        categorizador.excluir_regra(regra_id)


def test_sem_regra_correspondente_retorna_none(categoria_despesa):
    assert categorizador.categorizar_descricao("Algo Sem Nenhuma Regra Pytest", "despesa") is None


def test_ignora_caixa_e_espacos_sem_alterar_descricao_original(categoria_despesa):
    regra_id = categorizador.criar_regra("IFOOD", "contem", categoria_despesa, prioridade=10)
    try:
        descricao_original = "   ifood *delivery   "
        resultado = categorizador.categorizar_descricao(descricao_original, "despesa")
        assert resultado == categoria_despesa
        assert descricao_original == "   ifood *delivery   "  # não foi alterada
    finally:
        categorizador.excluir_regra(regra_id)
