"""Testes do módulo de analytics (src/analise_financeira.py).

Usa uma data de referência fixa (REFERENCIA) em vez de date.today() em todo
teste, para o resultado não depender de quando a suíte é executada.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from src import analise_financeira as af
from src import categorias, contas, transacoes
from src.banco_de_dados import definir_usuario_atual

REFERENCIA = date(2026, 10, 15)  # 15/10 -> 15 dias decorridos de 31 no mês


def _criar_despesa(conta_id, categoria_id, valor, data_transacao, descricao="Despesa teste"):
    return transacoes.criar_transacao(
        tipo="despesa",
        descricao=descricao,
        valor=Decimal(str(valor)),
        data_transacao=data_transacao,
        conta_id=conta_id,
        categoria_id=categoria_id,
        origem="manual",
    )


def _criar_receita(conta_id, categoria_id, valor, data_transacao, descricao="Receita teste"):
    return transacoes.criar_transacao(
        tipo="receita",
        descricao=descricao,
        valor=Decimal(str(valor)),
        data_transacao=data_transacao,
        conta_id=conta_id,
        categoria_id=categoria_id,
        origem="manual",
    )


@pytest.fixture
def cenario_basico(conta_a, categoria_despesa, categoria_receita):
    ids = []
    try:
        ids.append(_criar_receita(conta_a, categoria_receita, "6500.00", date(2026, 10, 1)))
        ids.append(_criar_despesa(conta_a, categoria_despesa, "1450.00", date(2026, 10, 5)))
        yield {
            "conta_id": conta_a,
            "categoria_despesa": categoria_despesa,
            "categoria_receita": categoria_receita,
        }
    finally:
        for tid in ids:
            try:
                transacoes.excluir_transacao(tid)
            except Exception:
                pass


# ---------------------------------------------------------------------
# Receita/despesa por categoria, percentual e ranking
# ---------------------------------------------------------------------
def test_receitas_por_categoria_calcula_percentual(cenario_basico):
    linhas = af.receitas_por_categoria(date(2026, 10, 1), REFERENCIA)
    assert len(linhas) == 1
    assert linhas[0]["total"] == Decimal("6500.00")
    assert linhas[0]["percentual"] == Decimal("100")


def test_despesas_por_categoria_ranking_ordenado_desc(conta_a, categoria_despesa):
    ids = [
        _criar_despesa(conta_a, categoria_despesa, "100.00", date(2026, 10, 2), "Pequena"),
        _criar_despesa(conta_a, categoria_despesa, "900.00", date(2026, 10, 3), "Grande"),
    ]
    try:
        linhas = af.despesas_por_categoria(date(2026, 10, 1), REFERENCIA)
        assert linhas[0]["total"] == Decimal("1000.00")  # soma da mesma categoria
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


def test_maior_fonte_receita(cenario_basico):
    maior = af.maior_fonte_receita(date(2026, 10, 1), REFERENCIA)
    assert maior["percentual"] == Decimal("100")


def test_categoria_maior_gasto(cenario_basico):
    maior = af.categoria_maior_gasto(date(2026, 10, 1), REFERENCIA)
    assert maior["total"] == Decimal("1450.00")


def test_concentracao_receita_sem_receita_retorna_none(conta_a):
    assert af.concentracao_receita(date(2026, 10, 1), REFERENCIA) is None


# ---------------------------------------------------------------------
# Comparação histórica (este mês / mês passado / média 3 meses)
# ---------------------------------------------------------------------
def test_comparar_categoria_historico_media_3_meses(conta_a, categoria_despesa):
    ids = [
        _criar_despesa(conta_a, categoria_despesa, "1450.00", date(2026, 10, 5)),
        _criar_despesa(conta_a, categoria_despesa, "1170.00", date(2026, 9, 5)),
        _criar_despesa(conta_a, categoria_despesa, "1080.00", date(2026, 8, 5)),
        _criar_despesa(conta_a, categoria_despesa, "990.00", date(2026, 7, 5)),
    ]
    try:
        resultado = af.comparar_categoria_historico(categoria_despesa, "despesa", REFERENCIA)
        assert resultado["este_mes"] == Decimal("1450.00")
        assert resultado["mes_passado"] == Decimal("1170.00")
        assert resultado["media_3_meses"] == (
            Decimal("1170.00") + Decimal("1080.00") + Decimal("990.00")
        ) / Decimal("3")
        assert resultado["variacao_vs_media_percentual"] > Decimal("0")
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


def test_comparar_categoria_historico_apenas_um_mes_disponivel(conta_a, categoria_despesa):
    tid = _criar_despesa(conta_a, categoria_despesa, "500.00", date(2026, 10, 5))
    try:
        resultado = af.comparar_categoria_historico(categoria_despesa, "despesa", REFERENCIA)
        assert resultado["mes_passado"] == Decimal("0")
        assert resultado["media_3_meses"] == Decimal("0")
        assert resultado["variacao_vs_media_percentual"] is None  # sem base para variação
    finally:
        transacoes.excluir_transacao(tid)


# ---------------------------------------------------------------------
# Tendências (crescimento/queda em 3 meses consecutivos)
# ---------------------------------------------------------------------
def test_detectar_padrao_consecutivo_crescimento():
    serie = [Decimal("100"), Decimal("150"), Decimal("200"), Decimal("300")]
    assert af.detectar_padrao_consecutivo(serie) == "crescimento"


def test_detectar_padrao_consecutivo_queda():
    serie = [Decimal("300"), Decimal("200"), Decimal("150"), Decimal("100")]
    assert af.detectar_padrao_consecutivo(serie) == "queda"


def test_detectar_padrao_consecutivo_sem_padrao_claro():
    serie = [Decimal("100"), Decimal("300"), Decimal("100"), Decimal("300")]
    assert af.detectar_padrao_consecutivo(serie) is None


def test_detectar_padrao_consecutivo_amostra_insuficiente():
    assert af.detectar_padrao_consecutivo([Decimal("100"), Decimal("200")]) is None


def test_evolucao_mensal_categoria_meses_sem_dados_vem_como_zero(conta_a, categoria_despesa):
    tid = _criar_despesa(conta_a, categoria_despesa, "500.00", date(2026, 10, 5))
    try:
        serie = af.evolucao_mensal_categoria(categoria_despesa, "despesa", meses=4, referencia=REFERENCIA)
        assert len(serie) == 4
        assert serie[-1]["valor"] == Decimal("500.00")
        assert serie[0]["valor"] == Decimal("0")
    finally:
        transacoes.excluir_transacao(tid)


# ---------------------------------------------------------------------
# Taxa de economia
# ---------------------------------------------------------------------
def test_taxa_economia_calculo_basico():
    taxa = af.taxa_economia(Decimal("1000"), Decimal("720"))
    assert taxa == Decimal("28.0")


def test_taxa_economia_sem_receita_retorna_none():
    assert af.taxa_economia(Decimal("0"), Decimal("100")) is None


def test_taxa_economia_periodo(cenario_basico):
    resultado = af.taxa_economia_periodo(date(2026, 10, 1), REFERENCIA)
    esperado = (Decimal("6500.00") - Decimal("1450.00")) / Decimal("6500.00") * Decimal("100")
    assert resultado["taxa"] == esperado


# ---------------------------------------------------------------------
# Projeção do mês
# ---------------------------------------------------------------------
def test_projetar_gasto_mes_formula_simples(conta_a, categoria_despesa):
    tid = _criar_despesa(conta_a, categoria_despesa, "750.00", date(2026, 10, 10))
    try:
        resultado = af.projetar_gasto_mes(REFERENCIA)
        assert resultado["dias_decorridos"] == 15
        assert resultado["dias_do_mes"] == 31
        media_diaria = Decimal("750.00") / Decimal("15")
        assert resultado["projecao_fim_mes"] == (media_diaria * Decimal("31")).quantize(Decimal("0.01"))
        assert resultado["confianca_baixa"] is False
    finally:
        transacoes.excluir_transacao(tid)


def test_projetar_gasto_mes_poucos_dias_marca_confianca_baixa(conta_a, categoria_despesa):
    tid = _criar_despesa(conta_a, categoria_despesa, "100.00", date(2026, 10, 2))
    try:
        resultado = af.projetar_gasto_mes(date(2026, 10, 2))
        assert resultado["confianca_baixa"] is True
    finally:
        transacoes.excluir_transacao(tid)


# ---------------------------------------------------------------------
# Insights determinísticos
# ---------------------------------------------------------------------
def test_gerar_insights_concentracao_de_renda(conta_a, categoria_receita):
    tid = _criar_receita(conta_a, categoria_receita, "6500.00", date(2026, 10, 1))
    try:
        insights = af.gerar_insights(REFERENCIA)
        assert any("única categoria" in texto for texto in insights)
    finally:
        transacoes.excluir_transacao(tid)


def test_gerar_insights_sem_dados_retorna_lista_vazia(conta_a):
    assert af.gerar_insights(REFERENCIA) == []


# ---------------------------------------------------------------------
# Detecção de gastos fora do padrão (IQR)
# ---------------------------------------------------------------------
def test_detectar_anomalia_com_amostra_suficiente(conta_a, categoria_despesa):
    ids = [
        _criar_despesa(conta_a, categoria_despesa, "50.00", date(2026, 10, 1)),
        _criar_despesa(conta_a, categoria_despesa, "55.00", date(2026, 10, 2)),
        _criar_despesa(conta_a, categoria_despesa, "48.00", date(2026, 10, 3)),
        _criar_despesa(conta_a, categoria_despesa, "52.00", date(2026, 10, 4)),
        _criar_despesa(conta_a, categoria_despesa, "1000.00", date(2026, 10, 5), "Fora do padrão"),
    ]
    try:
        anomalias = af.detectar_lancamentos_fora_padrao(categoria_despesa, date(2026, 10, 1), REFERENCIA)
        assert len(anomalias) == 1
        assert anomalias[0]["descricao"] == "Fora do padrão"
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


def test_detectar_anomalia_amostra_insuficiente_nao_marca_nada(conta_a, categoria_despesa):
    ids = [
        _criar_despesa(conta_a, categoria_despesa, "50.00", date(2026, 10, 1)),
        _criar_despesa(conta_a, categoria_despesa, "1000.00", date(2026, 10, 2)),
    ]
    try:
        anomalias = af.detectar_lancamentos_fora_padrao(categoria_despesa, date(2026, 10, 1), REFERENCIA)
        assert anomalias == []
    finally:
        for tid in ids:
            transacoes.excluir_transacao(tid)


# ---------------------------------------------------------------------
# Isolamento por usuário: analytics nunca mistura dados de usuários
# ---------------------------------------------------------------------
def test_analytics_isolado_por_usuario(usuario_a_id, usuario_b_id):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Analytics A", "conta_corrente", None, Decimal("0"))
    categoria_a_id = categorias.criar_categoria("Categoria Analytics A", "despesa")
    tid_a = _criar_despesa(conta_a_id, categoria_a_id, "100.00", date(2026, 10, 5))

    definir_usuario_atual(usuario_b_id)
    conta_b_id = contas.criar_conta("Conta Analytics B", "conta_corrente", None, Decimal("0"))
    categoria_b_id = categorias.criar_categoria("Categoria Analytics B", "despesa")
    tid_b = _criar_despesa(conta_b_id, categoria_b_id, "999999.00", date(2026, 10, 5))

    try:
        # analytics do usuario A não deve ver nem ser influenciado pelos
        # dados (muito maiores) do usuario B
        definir_usuario_atual(usuario_a_id)
        despesas_a = af.despesas_por_categoria(date(2026, 10, 1), REFERENCIA)
        assert len(despesas_a) == 1
        assert despesas_a[0]["total"] == Decimal("100.00")

        definir_usuario_atual(usuario_b_id)
        despesas_b = af.despesas_por_categoria(date(2026, 10, 1), REFERENCIA)
        assert len(despesas_b) == 1
        assert despesas_b[0]["total"] == Decimal("999999.00")
    finally:
        definir_usuario_atual(usuario_a_id)
        transacoes.excluir_transacao(tid_a)
        categorias.excluir_categoria(categoria_a_id)
        contas.excluir_conta(conta_a_id)

        definir_usuario_atual(usuario_b_id)
        transacoes.excluir_transacao(tid_b)
        categorias.excluir_categoria(categoria_b_id)
        contas.excluir_conta(conta_b_id)
