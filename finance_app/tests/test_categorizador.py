from datetime import date
from decimal import Decimal

import pytest

from src import categorias, categorizador, transacoes

# Prefixo único usado em todas as descrições de teste de categorização
# retroativa: garante que nenhuma regra/transação real do usuário possa
# jamais corresponder a estes dados sintéticos, mesmo rodando contra um
# banco com dados reais.
_PREFIXO = "ZZPYRETRO"


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


# =======================================================================
# Categorização retroativa (buscar/aplicar em lançamentos existentes)
# =======================================================================
def test_retroativo_operador_contem(conta_a, categoria_despesa):
    regra_id = categorizador.criar_regra(_PREFIXO + "CONTEM", "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"Compra {_PREFIXO}CONTEM Delivery", valor=Decimal("30"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid in ids
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_operador_igual(conta_a, categoria_despesa):
    texto = _PREFIXO + "IGUAL"
    regra_id = categorizador.criar_regra(texto, "igual", categoria_despesa, prioridade=10)
    tid_igual = transacoes.criar_transacao(
        tipo="despesa", descricao=texto, valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    tid_parcial = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Extra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid_igual in ids
        assert tid_parcial not in ids
    finally:
        transacoes.excluir_transacao(tid_igual)
        transacoes.excluir_transacao(tid_parcial)
        categorizador.excluir_regra(regra_id)


def test_retroativo_operador_comeca_com(conta_a, categoria_despesa):
    texto = _PREFIXO + "START"
    regra_id = categorizador.criar_regra(texto, "comeca_com", categoria_despesa, prioridade=10)
    tid_inicio = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Loja", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    tid_meio = transacoes.criar_transacao(
        tipo="despesa", descricao=f"Loja {texto}", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid_inicio in ids
        assert tid_meio not in ids
    finally:
        transacoes.excluir_transacao(tid_inicio)
        transacoes.excluir_transacao(tid_meio)
        categorizador.excluir_regra(regra_id)


def test_retroativo_varias_transacoes_compativeis(conta_a, categoria_despesa):
    texto = _PREFIXO + "MULTI"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    ids_criados = [
        transacoes.criar_transacao(
            tipo="despesa", descricao=f"{texto} {i}", valor=Decimal("10"),
            data_transacao=date(2020, 1, 1), conta_id=conta_a,
        )
        for i in range(3)
    ]
    try:
        encontrados = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert set(ids_criados).issubset(encontrados)
    finally:
        for tid in ids_criados:
            transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_transacao_sem_categoria_e_categorizada(conta_a, categoria_despesa):
    texto = _PREFIXO + "APLICA"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        total = categorizador.aplicar_regra_em_transacoes_existentes(regra_id, transacao_ids=[tid])
        assert total == 1
        assert transacoes.obter_transacao(tid)["categoria_id"] == categoria_despesa
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_transacao_ja_categorizada_nao_alterada_por_padrao(conta_a, categoria_despesa):
    texto = _PREFIXO + "MANTEM"
    outra_categoria_id = categorias.criar_categoria(_PREFIXO + " Outra Categoria", "despesa")
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a, categoria_id=outra_categoria_id,
    )
    try:
        total = categorizador.aplicar_regra_em_transacoes_existentes(regra_id, transacao_ids=[tid])
        assert total == 0
        assert transacoes.obter_transacao(tid)["categoria_id"] == outra_categoria_id
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)
        categorias.excluir_categoria(outra_categoria_id)


def test_retroativo_substituicao_explicita(conta_a, categoria_despesa):
    texto = _PREFIXO + "SUBST"
    outra_categoria_id = categorias.criar_categoria(_PREFIXO + " Outra Categoria 2", "despesa")
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a, categoria_id=outra_categoria_id,
    )
    try:
        total = categorizador.aplicar_regra_em_transacoes_existentes(
            regra_id, transacao_ids=[tid], somente_sem_categoria=False
        )
        assert total == 1
        assert transacoes.obter_transacao(tid)["categoria_id"] == categoria_despesa
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)
        categorias.excluir_categoria(outra_categoria_id)


def test_retroativo_categoria_incompativel_com_tipo(conta_a, categoria_receita):
    texto = _PREFIXO + "TIPO"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_receita, prioridade=10)
    tid_despesa = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid_despesa not in ids
        total = categorizador.aplicar_regra_em_transacoes_existentes(
            regra_id, transacao_ids=[tid_despesa]
        )
        assert total == 0
    finally:
        transacoes.excluir_transacao(tid_despesa)
        categorizador.excluir_regra(regra_id)


def test_retroativo_categoria_ambos_aceita_receita_e_despesa(conta_a):
    texto = _PREFIXO + "AMBOS"
    categoria_ambos_id = categorias.criar_categoria(_PREFIXO + " Cat Ambos", "ambos")
    regra_id = categorizador.criar_regra(texto, "contem", categoria_ambos_id, prioridade=10)
    tid_despesa = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} D", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    tid_receita = transacoes.criar_transacao(
        tipo="receita", descricao=f"{texto} R", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid_despesa in ids
        assert tid_receita in ids
    finally:
        transacoes.excluir_transacao(tid_despesa)
        transacoes.excluir_transacao(tid_receita)
        categorizador.excluir_regra(regra_id)
        categorias.excluir_categoria(categoria_ambos_id)


def test_retroativo_transferencia_ignorada(conta_a, conta_b, categoria_despesa):
    texto = _PREFIXO + "TRANSF"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid_transf = transacoes.criar_transacao(
        tipo="transferencia", descricao=texto, valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a, conta_destino_id=conta_b,
    )
    try:
        ids = {t["id"] for t in categorizador.buscar_transacoes_compativeis_regra(regra_id)}
        assert tid_transf not in ids
    finally:
        transacoes.excluir_transacao(tid_transf)
        categorizador.excluir_regra(regra_id)


def test_retroativo_regra_inativa_ignorada(conta_a, categoria_despesa):
    texto = _PREFIXO + "INATIVA"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    categorizador.atualizar_regra(regra_id, ativa=False)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        assert categorizador.buscar_transacoes_compativeis_regra(regra_id) == []
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_prioridade_das_regras(conta_a):
    texto = _PREFIXO + "PRIOR"
    cat_a = categorias.criar_categoria(_PREFIXO + " Prioridade A", "despesa")
    cat_b = categorias.criar_categoria(_PREFIXO + " Prioridade B", "despesa")
    regra_baixa = categorizador.criar_regra(texto, "contem", cat_a, prioridade=1)
    regra_alta = categorizador.criar_regra(texto, "contem", cat_b, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        total = categorizador.aplicar_todas_regras_em_transacoes_sem_categoria([tid])
        assert total == 1
        assert transacoes.obter_transacao(tid)["categoria_id"] == cat_b  # maior prioridade vence
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_baixa)
        categorizador.excluir_regra(regra_alta)
        categorias.excluir_categoria(cat_a)
        categorias.excluir_categoria(cat_b)


def test_retroativo_aplicacao_individual(conta_a, categoria_despesa):
    texto = _PREFIXO + "INDIVIDUAL"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        # transacao_ids=None -> aplica a todas as compatíveis encontradas pela regra
        total = categorizador.aplicar_regra_em_transacoes_existentes(regra_id)
        assert total == 1
        assert transacoes.obter_transacao(tid)["categoria_id"] == categoria_despesa
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_aplicacao_em_lote(conta_a, categoria_despesa):
    texto = _PREFIXO + "LOTE"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    ids_criados = [
        transacoes.criar_transacao(
            tipo="despesa", descricao=f"{texto} {i}", valor=Decimal("10"),
            data_transacao=date(2020, 1, 1), conta_id=conta_a,
        )
        for i in range(3)
    ]
    try:
        total = categorizador.aplicar_regra_em_transacoes_existentes(
            regra_id, transacao_ids=ids_criados
        )
        assert total == 3
        for tid in ids_criados:
            assert transacoes.obter_transacao(tid)["categoria_id"] == categoria_despesa
    finally:
        for tid in ids_criados:
            transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)


def test_retroativo_reaplicacao_de_todas_as_regras(conta_a):
    texto1 = _PREFIXO + "TODAS1"
    texto2 = _PREFIXO + "TODAS2"
    texto3 = _PREFIXO + "TODAS3"
    cat_a = categorias.criar_categoria(_PREFIXO + " Reaplicar A", "despesa")
    cat_b = categorias.criar_categoria(_PREFIXO + " Reaplicar B", "receita")
    regra_a = categorizador.criar_regra(texto1, "contem", cat_a, prioridade=5)
    regra_b = categorizador.criar_regra(texto2, "contem", cat_b, prioridade=5)
    tid1 = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto1} Compra", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    tid2 = transacoes.criar_transacao(
        tipo="receita", descricao=f"{texto2} Receita", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    tid3 = transacoes.criar_transacao(
        tipo="despesa", descricao=f"Sem correspondência {texto3}", valor=Decimal("10"),
        data_transacao=date(2020, 1, 1), conta_id=conta_a,
    )
    try:
        # Filtra a prévia global apenas para os ids criados por este teste —
        # nunca aplica a nenhuma transação que não tenha sido criada aqui,
        # mesmo que a prévia (que varre todo o banco) retorne outras linhas.
        ids_meus = {tid1, tid2, tid3}
        previa_minha = [
            item for item in categorizador.prever_aplicacao_todas_regras() if item["id"] in ids_meus
        ]
        assert {item["id"] for item in previa_minha} == {tid1, tid2}  # tid3 não corresponde a nada

        total = categorizador.aplicar_todas_regras_em_transacoes_sem_categoria(
            [item["id"] for item in previa_minha]
        )
        assert total == 2
        assert transacoes.obter_transacao(tid1)["categoria_id"] == cat_a
        assert transacoes.obter_transacao(tid2)["categoria_id"] == cat_b
        assert transacoes.obter_transacao(tid3)["categoria_id"] is None
    finally:
        for tid in (tid1, tid2, tid3):
            transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_a)
        categorizador.excluir_regra(regra_b)
        categorias.excluir_categoria(cat_a)
        categorias.excluir_categoria(cat_b)


def test_retroativo_nenhum_outro_campo_alterado(conta_a, categoria_despesa):
    texto = _PREFIXO + "CAMPOS"
    regra_id = categorizador.criar_regra(texto, "contem", categoria_despesa, prioridade=10)
    tid = transacoes.criar_transacao(
        tipo="despesa", descricao=f"{texto} Compra", valor=Decimal("42.50"),
        data_transacao=date(2020, 5, 15), conta_id=conta_a, observacao="obs original",
    )
    try:
        antes = transacoes.obter_transacao(tid)
        categorizador.aplicar_regra_em_transacoes_existentes(regra_id, transacao_ids=[tid])
        depois = transacoes.obter_transacao(tid)

        assert depois["categoria_id"] == categoria_despesa
        campos_imutaveis = [
            "descricao", "valor", "data_transacao", "conta_id", "cartao_id",
            "origem", "observacao", "grupo_parcelamento", "numero_parcela",
            "total_parcelas", "conta_destino_id", "tipo", "recorrencia_id", "fatura_id",
        ]
        for campo in campos_imutaveis:
            assert antes[campo] == depois[campo], f"campo {campo} foi alterado indevidamente"
    finally:
        transacoes.excluir_transacao(tid)
        categorizador.excluir_regra(regra_id)
