"""Leitura de arquivos OFX.

Reaproveita ao máximo o pipeline já usado pela importação de CSV
(src/importador.py): a única parte específica de OFX aqui é extrair data,
descrição e valor de cada transação do arquivo. Classificação
receita/despesa (pelo sinal do valor), parsing de data/valor e a montagem
do dict de linha são o mesmo código usado para CSV — processar_linha.

OFX não tem conceito de "coluna de tipo" mapeável pelo usuário como o CSV:
o tipo é sempre inferido pelo sinal do valor (positivo -> receita, negativo
-> despesa), exatamente como no CSV quando nenhuma coluna de tipo é
selecionada.
"""

import io

from src.importador import processar_linha


def ler_transacoes_ofx(conteudo: bytes) -> list[dict]:
    """Lê um arquivo OFX e retorna uma lista de linhas no mesmo formato
    produzido por importador.processar_linha (usado também pelo CSV),
    prontas para passar pelas mesmas etapas de categorização e checagem de
    duplicidade da importação de CSV.

    Levanta ValueError com mensagem amigável se o arquivo não puder ser
    interpretado como OFX válido.
    """
    from ofxparse import OfxParser  # import local: biblioteca só é necessária aqui

    if not conteudo or not conteudo.strip():
        raise ValueError("O arquivo está vazio.")

    try:
        ofx = OfxParser.parse(io.BytesIO(conteudo))
    except Exception as exc:
        raise ValueError(
            "Não foi possível interpretar o arquivo OFX. Verifique se o "
            "arquivo não está corrompido ou exporte-o novamente do seu banco."
        ) from exc

    contas_ofx = getattr(ofx, "accounts", None) or [ofx.account]

    linhas = []
    indice = 0
    for conta_ofx in contas_ofx:
        extrato = getattr(conta_ofx, "statement", None)
        if extrato is None:
            continue
        for transacao in extrato.transactions:
            descricao_bruta = (
                getattr(transacao, "memo", None) or getattr(transacao, "payee", None) or ""
            ).strip()
            data_bruta = transacao.date.date().isoformat()
            valor_bruto = str(transacao.amount)

            linha = processar_linha(
                data_bruta=data_bruta,
                descricao_bruta=descricao_bruta,
                valor_bruto=valor_bruto,
            )
            linha["indice"] = indice
            linha["fitid"] = getattr(transacao, "id", None)
            linhas.append(linha)
            indice += 1

    if not linhas:
        raise ValueError("O arquivo OFX não contém nenhuma transação.")

    return linhas
