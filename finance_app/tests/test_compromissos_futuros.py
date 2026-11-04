"""Testes de projetar_proximas_ocorrencias (src/recorrencias.py) e
compromissos_previstos (src/compromissos_futuros.py) — Parte 16."""

from datetime import date
from decimal import Decimal

from src import compromissos_futuros, recorrencias


def test_projetar_proximas_ocorrencias_mensal(conta_a, categoria_despesa):
    rid = recorrencias.criar_recorrencia(
        "despesa", "Aluguel", Decimal("1500"), conta_a, "mensal", date(2026, 1, 15),
        categoria_id=categoria_despesa,
    )
    try:
        datas = recorrencias.projetar_proximas_ocorrencias(rid, quantidade=3)
        assert datas == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]
    finally:
        recorrencias.excluir_recorrencia(rid)


def test_projetar_proximas_ocorrencias_respeita_data_fim(conta_a, categoria_despesa):
    rid = recorrencias.criar_recorrencia(
        "despesa", "Assinatura", Decimal("50"), conta_a, "mensal", date(2026, 1, 1),
        categoria_id=categoria_despesa, data_fim=date(2026, 2, 28),
    )
    try:
        datas = recorrencias.projetar_proximas_ocorrencias(rid, quantidade=6)
        assert datas == [date(2026, 1, 1), date(2026, 2, 1)]
    finally:
        recorrencias.excluir_recorrencia(rid)


def test_projetar_proximas_ocorrencias_inativa_retorna_vazio(conta_a, categoria_despesa):
    rid = recorrencias.criar_recorrencia(
        "despesa", "Cancelada", Decimal("50"), conta_a, "mensal", date(2026, 1, 1),
        categoria_id=categoria_despesa,
    )
    try:
        recorrencias.desativar_recorrencia(rid)
        assert recorrencias.projetar_proximas_ocorrencias(rid, quantidade=3) == []
    finally:
        recorrencias.excluir_recorrencia(rid)


def test_projetar_proximas_ocorrencias_ja_geradas_nao_repete(conta_a, categoria_despesa):
    rid = recorrencias.criar_recorrencia(
        "despesa", "Internet", Decimal("100"), conta_a, "mensal", date(2026, 1, 1),
        categoria_id=categoria_despesa,
    )
    try:
        recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 3, 1))
        # já geradas: jan, fev, mar. A próxima projeção deve começar em abril.
        datas = recorrencias.projetar_proximas_ocorrencias(rid, quantidade=2)
        assert datas == [date(2026, 4, 1), date(2026, 5, 1)]
    finally:
        from sqlalchemy import text

        from src.banco_de_dados import conexao_usuario

        with conexao_usuario() as conn:
            conn.execute(text("DELETE FROM transacoes WHERE recorrencia_id = :id"), {"id": rid})
        recorrencias.excluir_recorrencia(rid)


def test_compromissos_previstos_soma_parcelas_e_recorrencias(conta_a, categoria_despesa):
    from src import transacoes

    ids_parcelas = transacoes.criar_transacao_parcelada(
        tipo="despesa",
        descricao="Geladeira",
        valor_total=Decimal("1200.00"),
        data_primeira_parcela=date(2026, 1, 10),
        total_parcelas=3,
        conta_id=conta_a,
        categoria_id=categoria_despesa,
    )
    rid = recorrencias.criar_recorrencia(
        "despesa", "Streaming", Decimal("40"), conta_a, "mensal", date(2026, 1, 1),
        categoria_id=categoria_despesa,
    )
    try:
        resultado = compromissos_futuros.compromissos_previstos(meses=3, referencia=date(2026, 1, 1))
        assert len(resultado) == 3
        janeiro = resultado[0]
        assert janeiro["mes"] == date(2026, 1, 1)
        assert janeiro["parcelas_previstas"] == Decimal("400.00")
        assert janeiro["recorrencias_previstas"] == Decimal("40")
        assert janeiro["total_previsto"] == Decimal("440.00")
    finally:
        for tid in ids_parcelas:
            transacoes.excluir_transacao(tid)
        recorrencias.excluir_recorrencia(rid)


def test_compromissos_previstos_sem_dados_retorna_zeros(conta_a):
    resultado = compromissos_futuros.compromissos_previstos(meses=2, referencia=date(2026, 6, 1))
    assert len(resultado) == 2
    for item in resultado:
        assert item["total_previsto"] == Decimal("0")
