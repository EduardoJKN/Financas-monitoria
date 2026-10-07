"""Isolamento multiusuário (Parte 26): usuário A nunca consegue ler, alterar,
excluir ou inferir a existência de dados do usuário B — mesmo usando um ID
conhecido de um registro do outro usuário. Cobre contas, categorias,
transações, regras de categorização, metas, recorrências, cartões e
faturas/pagamentos.

Cada teste cria dados de A e de B, confirma o isolamento nos dois sentidos
e remove tudo ao final (nenhum dado de teste sobrevive à suíte)."""

from datetime import date
from decimal import Decimal

import pytest

from src import (
    cartoes,
    categorias,
    categorizador,
    contas,
    faturas,
    metas,
    recorrencias,
    transacoes,
)
from src.banco_de_dados import definir_usuario_atual


# ---------------------------------------------------------------------
# Contas
# ---------------------------------------------------------------------
def test_isolamento_contas(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Isolamento A", "conta_corrente", None, Decimal("100"))
    try:
        definir_usuario_atual(usuario_b_id)
        assert contas.obter_conta(conta_a_id) is None
        assert conta_a_id not in {c["id"] for c in contas.listar_contas(incluir_inativas=True)}
        with pytest.raises(ValueError):
            contas.atualizar_conta(conta_a_id, nome="Hackeado")
        with pytest.raises(ValueError):
            contas.excluir_conta(conta_a_id)

        definir_usuario_atual(usuario_a_id)
        intacta = contas.obter_conta(conta_a_id)
        assert intacta["nome"] == "Conta Isolamento A"
    finally:
        definir_usuario_atual(usuario_a_id)
        contas.excluir_conta(conta_a_id)


# ---------------------------------------------------------------------
# Categorias (inclui tentativa via categoria_pai_id de outro usuário)
# ---------------------------------------------------------------------
def test_isolamento_categorias(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    categoria_a_id = categorias.criar_categoria("Categoria Isolamento A", "despesa")
    try:
        definir_usuario_atual(usuario_b_id)
        assert categorias.obter_categoria(categoria_a_id) is None
        with pytest.raises(ValueError):
            categorias.atualizar_categoria(categoria_a_id, nome="Hackeado")
        with pytest.raises(ValueError):
            categorias.excluir_categoria(categoria_a_id)
        # tentar criar uma categoria filha usando o ID conhecido da categoria de A como pai
        with pytest.raises(ValueError):
            categorias.criar_categoria("Filha de categoria de outro usuario", "despesa", categoria_a_id)
    finally:
        definir_usuario_atual(usuario_a_id)
        categorias.excluir_categoria(categoria_a_id)


# ---------------------------------------------------------------------
# Transações (inclui tentativa de referenciar conta de outro usuário)
# ---------------------------------------------------------------------
def test_isolamento_transacoes(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Transacoes A", "conta_corrente", None, Decimal("0"))
    categoria_a_id = categorias.criar_categoria("Categoria Transacoes A", "despesa")
    transacao_a_id = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Despesa de A",
        valor=Decimal("50.00"),
        data_transacao=date(2026, 10, 1),
        conta_id=conta_a_id,
        categoria_id=categoria_a_id,
    )
    try:
        definir_usuario_atual(usuario_b_id)
        assert transacoes.obter_transacao(transacao_a_id) is None
        assert transacao_a_id not in {t["id"] for t in transacoes.listar_transacoes()}
        with pytest.raises(ValueError):
            transacoes.excluir_transacao(transacao_a_id)

        # B tenta criar uma transação usando o conta_id conhecido de A
        with pytest.raises(ValueError):
            transacoes.criar_transacao(
                tipo="despesa",
                descricao="Ataque via conta_id conhecido",
                valor=Decimal("10.00"),
                data_transacao=date(2026, 10, 1),
                conta_id=conta_a_id,
            )
    finally:
        definir_usuario_atual(usuario_a_id)
        transacoes.excluir_transacao(transacao_a_id)
        categorias.excluir_categoria(categoria_a_id)
        contas.excluir_conta(conta_a_id)


# ---------------------------------------------------------------------
# Regras de categorização
# ---------------------------------------------------------------------
def test_isolamento_regras_categorizacao(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    categoria_a_id = categorias.criar_categoria("Categoria Regra A", "despesa")
    regra_a_id = categorizador.criar_regra("supermercado xyz", "contem", categoria_a_id)
    try:
        definir_usuario_atual(usuario_b_id)
        assert categorizador.obter_regra(regra_a_id) is None
        assert regra_a_id not in {r["id"] for r in categorizador.listar_regras(incluir_inativas=True)}
        with pytest.raises(ValueError):
            categorizador.excluir_regra(regra_a_id)
        # categorizar_descricao de B nunca deve ser sugerida pela regra de A
        assert categorizador.categorizar_descricao("compra no supermercado xyz") is None
    finally:
        definir_usuario_atual(usuario_a_id)
        categorizador.excluir_regra(regra_a_id)
        categorias.excluir_categoria(categoria_a_id)


# ---------------------------------------------------------------------
# Metas
# ---------------------------------------------------------------------
def test_isolamento_metas(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    meta_a_id = metas.criar_meta("Meta Isolamento A", date(2026, 1, 1), Decimal("1000"))
    try:
        definir_usuario_atual(usuario_b_id)
        assert metas.obter_meta(meta_a_id) is None
        assert meta_a_id not in {m["id"] for m in metas.listar_metas()}
        with pytest.raises(ValueError):
            metas.atualizar_meta(meta_a_id, nome="Hackeada")
        with pytest.raises(ValueError):
            metas.excluir_meta(meta_a_id)
    finally:
        definir_usuario_atual(usuario_a_id)
        metas.excluir_meta(meta_a_id)


# ---------------------------------------------------------------------
# Recorrências (inclui tentativa de referenciar conta de outro usuário)
# ---------------------------------------------------------------------
def test_isolamento_recorrencias(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Recorrencia A", "conta_corrente", None, Decimal("0"))
    recorrencia_a_id = recorrencias.criar_recorrencia(
        "despesa", "Aluguel de A", Decimal("1000"), conta_a_id, "mensal", date(2026, 1, 1)
    )
    try:
        definir_usuario_atual(usuario_b_id)
        assert recorrencias.obter_recorrencia(recorrencia_a_id) is None
        assert recorrencia_a_id not in {
            r["id"] for r in recorrencias.listar_recorrencias(incluir_inativas=True)
        }
        with pytest.raises(ValueError):
            recorrencias.excluir_recorrencia(recorrencia_a_id)
        with pytest.raises(ValueError):
            recorrencias.criar_recorrencia(
                "despesa", "Ataque via conta_id conhecido", Decimal("10"),
                conta_a_id, "mensal", date(2026, 1, 1),
            )
    finally:
        definir_usuario_atual(usuario_a_id)
        recorrencias.excluir_recorrencia(recorrencia_a_id)
        contas.excluir_conta(conta_a_id)


# ---------------------------------------------------------------------
# Cartões, faturas e pagamentos
# ---------------------------------------------------------------------
def test_isolamento_cartoes_faturas_pagamentos(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Cartao A", "conta_corrente", None, Decimal("0"))
    cartao_a_id = cartoes.criar_cartao(
        "Cartao Isolamento A", Decimal("5000"), dia_fechamento=10, dia_vencimento=20,
        conta_pagamento_id=conta_a_id,
    )
    tid = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Compra no cartao de A",
        valor=Decimal("200.00"),
        data_transacao=date(2026, 10, 1),
        cartao_id=cartao_a_id,
    )
    compra = transacoes.obter_transacao(tid)
    fatura_a_id = compra["fatura_id"]
    try:
        definir_usuario_atual(usuario_b_id)
        assert cartoes.obter_cartao(cartao_a_id) is None
        assert cartao_a_id not in {c["id"] for c in cartoes.listar_cartoes(incluir_inativos=True)}
        assert faturas.obter_fatura(fatura_a_id) is None
        with pytest.raises(ValueError):
            cartoes.excluir_cartao(cartao_a_id)
        # B tenta pagar a fatura de A usando o ID conhecido
        with pytest.raises(ValueError):
            faturas.registrar_pagamento_fatura(fatura_a_id, conta_a_id, Decimal("10"), date(2026, 10, 15))
        # B tenta criar um cartão usando a conta de pagamento conhecida de A
        with pytest.raises(ValueError):
            cartoes.criar_cartao(
                "Cartao ataque", Decimal("100"), dia_fechamento=1, dia_vencimento=10,
                conta_pagamento_id=conta_a_id,
            )
    finally:
        definir_usuario_atual(usuario_a_id)
        transacoes.excluir_transacao(tid)
        from sqlalchemy import text

        from src.banco_de_dados import conexao_usuario

        with conexao_usuario() as conn:
            conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a_id})
        cartoes.excluir_cartao(cartao_a_id)
        contas.excluir_conta(conta_a_id)
