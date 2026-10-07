from datetime import date
from decimal import Decimal

import pytest

from src import transacoes


def test_criar_obter_transacao_despesa(conta_a, categoria_despesa):
    tid = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Compra Pytest",
        valor=Decimal("50.00"),
        data_transacao=date(2026, 10, 1),
        conta_id=conta_a,
        categoria_id=categoria_despesa,
    )
    try:
        t = transacoes.obter_transacao(tid)
        assert t["tipo"] == "despesa"
        assert t["valor"] == Decimal("50.00")
        assert t["origem"] == "manual"
    finally:
        transacoes.excluir_transacao(tid)


def test_transferencia_exige_conta_destino_diferente(conta_a):
    with pytest.raises(ValueError):
        transacoes.criar_transacao(
            tipo="transferencia",
            descricao="Transferência inválida",
            valor=Decimal("10"),
            data_transacao=date(2026, 10, 1),
            conta_id=conta_a,
            conta_destino_id=conta_a,
        )


def test_transferencia_entre_contas(conta_a, conta_b):
    tid = transacoes.criar_transacao(
        tipo="transferencia",
        descricao="Transferência Pytest",
        valor=Decimal("100"),
        data_transacao=date(2026, 10, 1),
        conta_id=conta_a,
        conta_destino_id=conta_b,
    )
    try:
        t = transacoes.obter_transacao(tid)
        assert t["conta_id"] == conta_a
        assert t["conta_destino_id"] == conta_b
    finally:
        transacoes.excluir_transacao(tid)


def test_despesa_exige_conta_ou_cartao_nunca_os_dois(conta_a, cartao_a):
    with pytest.raises(ValueError):
        transacoes.criar_transacao(
            tipo="despesa",
            descricao="Dupla forma de pagamento",
            valor=Decimal("10"),
            data_transacao=date(2026, 10, 1),
            conta_id=conta_a,
            cartao_id=cartao_a,
        )


def test_despesa_sem_conta_nem_cartao_levanta_erro():
    with pytest.raises(ValueError):
        transacoes.criar_transacao(
            tipo="despesa",
            descricao="Sem forma de pagamento",
            valor=Decimal("10"),
            data_transacao=date(2026, 10, 1),
        )


def test_categoria_incompativel_com_tipo(conta_a, categoria_receita):
    with pytest.raises(ValueError):
        transacoes.criar_transacao(
            tipo="despesa",
            descricao="Categoria errada",
            valor=Decimal("10"),
            data_transacao=date(2026, 10, 1),
            conta_id=conta_a,
            categoria_id=categoria_receita,
        )


# ---------------------------------------------------------------------
# Parcelamento
# ---------------------------------------------------------------------
def test_calcular_parcelas_soma_exata_sem_erro_de_centavos():
    valores = transacoes.calcular_parcelas(Decimal("1000"), 3)
    assert valores == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert sum(valores) == Decimal("1000.00")


def test_calcular_parcelas_total_parcelas_minimo_dois():
    with pytest.raises(ValueError):
        transacoes.calcular_parcelas(Decimal("100"), 1)


def test_simular_parcelas_datas_avancam_mes_a_mes_tratando_fim_de_mes():
    preview = transacoes.simular_parcelas(Decimal("600"), date(2026, 1, 31), 3)
    assert [p["data"] for p in preview] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]


def test_criar_transacao_parcelada_atomica_e_consistente(conta_a, categoria_despesa):
    ids = transacoes.criar_transacao_parcelada(
        tipo="despesa",
        descricao="Compra Parcelada Pytest",
        valor_total=Decimal("1000"),
        data_primeira_parcela=date(2026, 1, 31),
        total_parcelas=3,
        conta_id=conta_a,
        categoria_id=categoria_despesa,
    )
    try:
        assert len(ids) == 3
        parcelas = [transacoes.obter_transacao(tid) for tid in ids]
        assert sum(p["valor"] for p in parcelas) == Decimal("1000.00")
        grupos = {p["grupo_parcelamento"] for p in parcelas}
        assert len(grupos) == 1  # todas compartilham o mesmo grupo
        assert [p["numero_parcela"] for p in parcelas] == [1, 2, 3]
        assert all(p["total_parcelas"] == 3 for p in parcelas)
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


def test_criar_transacao_parcelada_nao_permite_transferencia(conta_a):
    with pytest.raises(ValueError):
        transacoes.criar_transacao_parcelada(
            tipo="transferencia",
            descricao="Transferência parcelada inválida",
            valor_total=Decimal("300"),
            data_primeira_parcela=date(2026, 1, 1),
            total_parcelas=3,
            conta_id=conta_a,
        )


def test_criar_transacao_parcelada_e_atomica_em_erro(conta_a, categoria_receita):
    # categoria incompatível (receita) com despesa -> nenhuma parcela deve ser criada
    with pytest.raises(ValueError):
        transacoes.criar_transacao_parcelada(
            tipo="despesa",
            descricao="Parcelamento que deve falhar",
            valor_total=Decimal("300"),
            data_primeira_parcela=date(2026, 1, 1),
            total_parcelas=3,
            conta_id=conta_a,
            categoria_id=categoria_receita,
        )
    restantes = transacoes.listar_transacoes(conta_id=conta_a)
    assert restantes == []


def test_atualizar_transacao_trocar_conta_para_cartao(conta_a, cartao_a, categoria_despesa):
    tid = transacoes.criar_transacao(
        tipo="despesa",
        descricao="Despesa que muda de forma de pagamento",
        valor=Decimal("50"),
        data_transacao=date(2026, 3, 10),
        conta_id=conta_a,
        categoria_id=categoria_despesa,
    )
    try:
        transacoes.atualizar_transacao(tid, conta_id=None, cartao_id=cartao_a)
        t = transacoes.obter_transacao(tid)
        assert t["conta_id"] is None
        assert t["cartao_id"] == cartao_a
        assert t["fatura_id"] is not None
    finally:
        transacoes.excluir_transacao(tid)
        # a mudança para cartão criou uma fatura; remove para não deixar
        # resíduo nem impedir a exclusão "de vez" do cartão pela fixture.
        from src.banco_de_dados import conexao_usuario
        from sqlalchemy import text

        with conexao_usuario() as conn:
            conn.execute(
                text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cartao_a}
            )
