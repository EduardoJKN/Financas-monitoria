"""Cenário financeiro completo de aceitação da V1, combinando todas as
funcionalidades do bloco: contas, cartão, parcelamento, pagamento de
fatura, recorrência (com geração idempotente), CSV e OFX (com duplicidade).

Roda contra o banco configurado em DATABASE_URL e remove todos os dados
criados ao final.
"""

import io
from datetime import date
from decimal import Decimal

from src import (
    cartoes,
    categorias,
    categorizador,
    contas,
    faturas,
    importador,
    metas,
    ofx as ofx_modulo,
    recorrencias,
    resumo_financeiro as resumo,
    transacoes,
)
from src.banco_de_dados import conexao_usuario


def test_cenario_financeiro_completo():
    criados = {
        "transacoes": [],
        "recorrencias": [],
        "metas": [],
        "cartoes": [],
        "categorias": [],
        "contas": [],
    }

    try:
        # 1. Contas: Nubank (2.000) e Itaú (1.000)
        nubank_id = contas.criar_conta("Nubank Aceitação", "conta_digital", None, Decimal("2000"))
        itau_id = contas.criar_conta("Itaú Aceitação", "conta_corrente", None, Decimal("1000"))
        criados["contas"] += [nubank_id, itau_id]

        cat_salario = categorias.criar_categoria("Salário Aceitação", "receita")
        cat_mercado = categorias.criar_categoria("Mercado Aceitação", "despesa")
        cat_compras = categorias.criar_categoria("Compras Aceitação", "despesa")
        cat_aluguel = categorias.criar_categoria("Aluguel Aceitação", "despesa")
        criados["categorias"] += [cat_salario, cat_mercado, cat_compras, cat_aluguel]

        # Cartão Nubank Mastercard, fecha dia 25, vence dia 5
        cartao_id = cartoes.criar_cartao(
            "Nubank Mastercard Aceitação", Decimal("5000"), dia_fechamento=25,
            dia_vencimento=5, conta_pagamento_id=nubank_id,
        )
        criados["cartoes"].append(cartao_id)

        # 2. Receita de salário: +5.000 na conta Nubank
        tid = transacoes.criar_transacao(
            tipo="receita", descricao="Salário Aceitação", valor=Decimal("5000"),
            data_transacao=date(2026, 3, 5), conta_id=nubank_id, categoria_id=cat_salario,
        )
        criados["transacoes"].append(tid)

        # 3. Mercado pago na conta: -500
        tid = transacoes.criar_transacao(
            tipo="despesa", descricao="Mercado Aceitação", valor=Decimal("500"),
            data_transacao=date(2026, 3, 6), conta_id=nubank_id, categoria_id=cat_mercado,
        )
        criados["transacoes"].append(tid)

        # 4. Transferência Nubank -> Itaú: 1.000
        tid = transacoes.criar_transacao(
            tipo="transferencia", descricao="Transferência Aceitação", valor=Decimal("1000"),
            data_transacao=date(2026, 3, 7), conta_id=nubank_id, conta_destino_id=itau_id,
        )
        criados["transacoes"].append(tid)

        assert resumo.calcular_saldo_conta(nubank_id) == Decimal("5500.00")  # 2000+5000-500-1000
        assert resumo.calcular_saldo_conta(itau_id) == Decimal("2000.00")  # 1000+1000

        # 5. Compra no cartão: 600 em 3x (parcelas de 200)
        ids_parcelas = transacoes.criar_transacao_parcelada(
            tipo="despesa", descricao="Compra Cartão Aceitação", valor_total=Decimal("600"),
            data_primeira_parcela=date(2026, 3, 10), total_parcelas=3, cartao_id=cartao_id,
            categoria_id=cat_compras,
        )
        criados["transacoes"] += ids_parcelas

        parcelas = [transacoes.obter_transacao(tid) for tid in ids_parcelas]
        assert all(p["valor"] == Decimal("200.00") for p in parcelas)

        faturas_das_parcelas = {p["fatura_id"] for p in parcelas}
        assert len(faturas_das_parcelas) == 3  # uma fatura por mês da parcela

        # saldo bancário ainda não reduzido pela compra parcelada (nenhum pagamento ainda)
        assert resumo.calcular_saldo_conta(nubank_id) == Decimal("5500.00")

        resultado_marco = resumo.calcular_resumo_periodo(date(2026, 3, 1), date(2026, 3, 31))
        assert resultado_marco["total_despesas"] == Decimal("700.00")  # 500 mercado + 200 1a parcela

        # 6. Paga a primeira fatura usando Nubank
        fatura_marco_id = parcelas[0]["fatura_id"]
        faturas.registrar_pagamento_fatura(
            fatura_marco_id, nubank_id, Decimal("200.00"), date(2026, 3, 26)
        )

        assert resumo.calcular_saldo_conta(nubank_id) == Decimal("5300.00")  # 5500 - 200
        fatura_marco = faturas.obter_fatura(fatura_marco_id)
        assert fatura_marco["status"] == "paga"

        resultado_marco_depois = resumo.calcular_resumo_periodo(date(2026, 3, 1), date(2026, 3, 31))
        assert resultado_marco_depois["total_despesas"] == Decimal("700.00")  # NÃO duplica

        # 7. Recorrência mensal (Aluguel)
        rec_id = recorrencias.criar_recorrencia(
            tipo="despesa", descricao="Aluguel Aceitação", valor=Decimal("1200"),
            conta_id=itau_id, periodicidade="mensal", data_inicio=date(2026, 3, 1),
            categoria_id=cat_aluguel,
        )
        criados["recorrencias"].append(rec_id)

        # 8. Gera lançamentos pendentes
        resumo_geracao_1 = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 3, 15))
        assert resumo_geracao_1["total_gerado"] == 1

        # 9. Executa novamente e confirma que não duplicou
        resumo_geracao_2 = recorrencias.gerar_lancamentos_pendentes(hoje=date(2026, 3, 15))
        assert resumo_geracao_2["total_gerado"] == 0

        geradas_recorrencia = transacoes.listar_transacoes(conta_id=itau_id, origem="recorrencia")
        criados["transacoes"] += [t["id"] for t in geradas_recorrencia]
        assert len(geradas_recorrencia) == 1

        # 10. Importa um CSV simples
        csv_texto = (
            "Data,Descricao,Valor\n"
            "08/03/2026,Compra CSV Aceitacao,-80.00\n"
        )
        linhas_csv = []
        for idx, linha_texto in enumerate(csv_texto.strip().split("\n")[1:]):
            data_b, desc_b, valor_b = linha_texto.split(",")
            linha = importador.processar_linha(data_b, desc_b, valor_b)
            linha["indice"] = idx
            linhas_csv.append(linha)
        assert linhas_csv[0]["status"] == "ok"
        tid = transacoes.criar_transacao(
            tipo=linhas_csv[0]["tipo"], descricao=linhas_csv[0]["descricao"],
            valor=linhas_csv[0]["valor"], data_transacao=linhas_csv[0]["data"],
            conta_id=nubank_id, origem="importacao",
        )
        criados["transacoes"].append(tid)

        # 11. Importa um OFX contendo uma transação duplicada (a mesma do CSV acima)
        ofx_bytes = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKACCTFROM>
<ACCTID>1
</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260308120000
<TRNAMT>-80.00
<FITID>9001
<MEMO>Compra CSV Aceitacao
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
""".encode("utf-8")

        linhas_ofx = ofx_modulo.ler_transacoes_ofx(ofx_bytes)
        assert len(linhas_ofx) == 1

        existentes = transacoes.listar_transacoes(
            conta_id=nubank_id, data_inicial=date(2026, 3, 8), data_final=date(2026, 3, 8)
        )
        chaves_existentes = {
            importador.chave_duplicidade(nubank_id, t["data_transacao"], t["tipo"], t["valor"], t["descricao"])
            for t in existentes
            if t["tipo"] != "transferencia"
        }
        chave_ofx = importador.chave_duplicidade(
            nubank_id, linhas_ofx[0]["data"], linhas_ofx[0]["tipo"], linhas_ofx[0]["valor"],
            linhas_ofx[0]["descricao"],
        )
        # 12. Confirma que a transação do OFX é detectada como duplicada e NÃO é reimportada
        assert chave_ofx in chaves_existentes

        # 13. Valida Visão Geral / contas / cartões / resultados
        saldos = resumo.calcular_saldos_contas()
        mapa_saldos = {s["conta_id"]: s["saldo"] for s in saldos}
        assert mapa_saldos[nubank_id] == resumo.calcular_saldo_conta(nubank_id)
        assert mapa_saldos[itau_id] == resumo.calcular_saldo_conta(itau_id)

        indicadores = resumo.calcular_indicadores_cartoes(hoje=date(2026, 3, 15))
        info_cartao = next(c for c in indicadores["cartoes"] if c["cartao_id"] == cartao_id)
        assert info_cartao["limite_utilizado"] == Decimal("400.00")  # 600 - 200 pagos

        categoria_sugerida = categorizador.categorizar_descricao("Compra CSV Aceitacao", "despesa")
        assert categoria_sugerida is None  # sem regra cadastrada, não quebra

    finally:
        for tid in criados["transacoes"]:
            try:
                transacoes.excluir_transacao(tid)
            except Exception:
                pass
        with conexao_usuario() as conn:
            from sqlalchemy import text

            for cid in criados["cartoes"]:
                conn.execute(text("DELETE FROM pagamentos_fatura WHERE fatura_id IN (SELECT id FROM faturas_cartao WHERE cartao_id = :id)"), {"id": cid})
                conn.execute(text("DELETE FROM faturas_cartao WHERE cartao_id = :id"), {"id": cid})
        for rid in criados["recorrencias"]:
            try:
                recorrencias.excluir_recorrencia(rid)
            except Exception:
                pass
        for mid in criados["metas"]:
            try:
                metas.excluir_meta(mid)
            except Exception:
                pass
        for cid in criados["cartoes"]:
            try:
                cartoes.excluir_cartao(cid)
            except Exception:
                pass
        for catid in criados["categorias"]:
            try:
                categorias.excluir_categoria(catid)
            except Exception:
                pass
        for contaid in criados["contas"]:
            try:
                contas.excluir_conta(contaid)
            except Exception:
                pass
