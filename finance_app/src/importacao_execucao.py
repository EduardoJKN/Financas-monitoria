"""Confirmação de uma linha já classificada de importação (CSV/OFX).

Extraído da página Streamlit de Importação para ser compartilhado também
pelo backend FastAPI — a decisão de como commitar uma linha (transferência
respeitando a direção correta, pagamento de fatura sem dupla contagem,
nunca convertendo silenciosamente para despesa comum) é lógica de negócio
e não deve existir duplicada em dois lugares.
"""

from datetime import date
from decimal import Decimal

from src import faturas, importador, transacoes

CLASSIFICACOES_VALIDAS = ("normal", "transferencia", "pagamento_fatura")


class ErroImportacao(ValueError):
    """Erro de confirmação de importação — mensagem sempre segura para
    exibir ao usuário final (nunca SQL/traceback)."""


def confirmar_linha(
    *,
    classificacao: str,
    tipo: str,
    descricao: str,
    valor: Decimal,
    data_transacao: date,
    conta_id_importacao: int,
    categoria_id: int | None = None,
    outra_conta_id: int | None = None,
    cartao_vinculado_id: int | None = None,
    origem: str = "importacao",
) -> dict:
    """Confirma uma linha já classificada, criando exatamente um efeito no
    banco: uma transação comum, uma transferência (com a direção correta
    — ver importador.resolver_contas_transferencia) ou um pagamento de
    fatura (nunca também uma despesa comum para a mesma compra). Retorna
    um dict com "tipo_resultado" e o id criado.

    Levanta ErroImportacao (subclasse de ValueError, compatível com o
    tratamento de erro já existente) para decisões impossíveis de
    concluir — nunca cai silenciosamente em outro comportamento."""
    if classificacao not in CLASSIFICACOES_VALIDAS:
        raise ErroImportacao(f"Classificação inválida: '{classificacao}'.")

    if classificacao == "transferencia":
        if outra_conta_id is None:
            raise ErroImportacao("Selecione a outra conta da transferência.")
        conta_id, conta_destino_id = importador.resolver_contas_transferencia(
            tipo, conta_id_importacao, outra_conta_id
        )
        novo_id = transacoes.criar_transacao(
            tipo="transferencia",
            descricao=descricao,
            valor=valor,
            data_transacao=data_transacao,
            conta_id=conta_id,
            conta_destino_id=conta_destino_id,
            origem=origem,
        )
        return {"tipo_resultado": "transacao", "transacao_id": novo_id}

    if classificacao == "pagamento_fatura":
        if cartao_vinculado_id is None:
            raise ErroImportacao("Selecione o cartão da fatura paga.")
        fatura = faturas.fatura_compativel_para_pagamento(cartao_vinculado_id, data_transacao)
        if fatura is None:
            raise ErroImportacao(
                "Nenhuma fatura compatível encontrada para o cartão escolhido. "
                "Escolha outro cartão, marque como despesa comum ou não importe esta linha."
            )
        pagamento_id = faturas.registrar_pagamento_fatura(
            fatura["id"], conta_id_importacao, valor, data_transacao
        )
        return {
            "tipo_resultado": "pagamento_fatura",
            "pagamento_id": pagamento_id,
            "fatura_id": fatura["id"],
        }

    novo_id = transacoes.criar_transacao(
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        data_transacao=data_transacao,
        conta_id=conta_id_importacao,
        categoria_id=categoria_id,
        origem=origem,
    )
    return {"tipo_resultado": "transacao", "transacao_id": novo_id}
