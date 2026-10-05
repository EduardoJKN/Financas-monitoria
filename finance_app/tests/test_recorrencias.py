from datetime import date
from decimal import Decimal

import pytest

from src import recorrencias, transacoes


def test_criar_listar_atualizar_desativar_excluir(conta_a, categoria_despesa):
    rec_id = recorrencias.criar_recorrencia(
        tipo="despesa",
        descricao="Aluguel Pytest",
        valor=Decimal("1500"),
        conta_id=conta_a,
        periodicidade="mensal",
        data_inicio=date(2026, 1, 1),
        categoria_id=categoria_despesa,
    )
    try:
        todas = recorrencias.listar_recorrencias(incluir_inativas=True)
        assert any(r["id"] == rec_id for r in todas)

        recorrencias.atualizar_recorrencia(rec_id, descricao="Aluguel Pytest Editado")
        r = recorrencias.obter_recorrencia(rec_id)
        assert r["descricao"] == "Aluguel Pytest Editado"

        recorrencias.desativar_recorrencia(rec_id)
        r = recorrencias.obter_recorrencia(rec_id)
        assert r["ativa"] is False
    finally:
        recorrencias.excluir_recorrencia(rec_id)
    assert recorrencias.obter_recorrencia(rec_id) is None


def test_data_fim_anterior_a_inicio_levanta_erro(conta_a, categoria_despesa):
    with pytest.raises(ValueError):
        recorrencias.criar_recorrencia(
            tipo="despesa",
            descricao="Recorrência inválida",
            valor=Decimal("100"),
            conta_id=conta_a,
            periodicidade="mensal",
            data_inicio=date(2026, 6, 1),
            data_fim=date(2026, 1, 1),
            categoria_id=categoria_despesa,
        )


def test_gerar_pendentes_e_idempotente_sem_deriva_de_fim_de_mes(conta_a, categoria_despesa):
    rec_id = recorrencias.criar_recorrencia(
        tipo="despesa",
        descricao="Aluguel Fim de Mês Pytest",
        valor=Decimal("1500"),
        conta_id=conta_a,
        periodicidade="mensal",
        data_inicio=date(2026, 1, 31),
        categoria_id=categoria_despesa,
    )
    try:
        resumo1 = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 4, 1))
        assert resumo1["total_gerado"] == 3  # jan, fev, mar

        resumo2 = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 4, 1))
        assert resumo2["total_gerado"] == 0  # idempotente: não duplica

        geradas = transacoes.listar_transacoes(conta_id=conta_a, origem="recorrencia")
        datas = sorted(t["data_transacao"] for t in geradas)
        # dia 31 preservado em março, sem ficar "travado" em 28 por causa de fevereiro
        assert datas == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]

        for t in geradas:
            transacoes.excluir_transacao(t["id"])
    finally:
        recorrencias.excluir_recorrencia(rec_id)


def test_gerar_pendentes_periodicidade_semanal(conta_a, categoria_despesa):
    rec_id = recorrencias.criar_recorrencia(
        tipo="despesa",
        descricao="Academia Semanal Pytest",
        valor=Decimal("50"),
        conta_id=conta_a,
        periodicidade="semanal",
        data_inicio=date(2026, 1, 5),
        categoria_id=categoria_despesa,
    )
    try:
        resumo = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 1, 26))
        assert resumo["total_gerado"] == 4  # 05, 12, 19, 26
        geradas = transacoes.listar_transacoes(conta_id=conta_a, origem="recorrencia")
        for t in geradas:
            transacoes.excluir_transacao(t["id"])
    finally:
        recorrencias.excluir_recorrencia(rec_id)


def test_gerar_pendentes_respeita_data_fim_e_desativa(conta_a, categoria_despesa):
    rec_id = recorrencias.criar_recorrencia(
        tipo="despesa",
        descricao="Assinatura com fim Pytest",
        valor=Decimal("30"),
        conta_id=conta_a,
        periodicidade="mensal",
        data_inicio=date(2026, 1, 1),
        data_fim=date(2026, 2, 28),
        categoria_id=categoria_despesa,
    )
    try:
        resumo = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 6, 1))
        assert resumo["total_gerado"] == 2  # jan e fev, não gera além de data_fim
        r = recorrencias.obter_recorrencia(rec_id)
        assert r["ativa"] is False  # desativada automaticamente após passar data_fim

        geradas = transacoes.listar_transacoes(conta_id=conta_a, origem="recorrencia")
        for t in geradas:
            transacoes.excluir_transacao(t["id"])
    finally:
        recorrencias.excluir_recorrencia(rec_id)
