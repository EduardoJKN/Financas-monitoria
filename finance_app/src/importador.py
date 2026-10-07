"""Lógica pura (sem I/O de banco) para importação de extratos CSV.

Mantido separado da página Streamlit para ser testável diretamente:
detecção de encoding/delimitador/cabeçalho, parsing de data e classificação
de cada linha em receita/despesa/erro/revisão.
"""

import csv
import unicodedata
from datetime import date, datetime

from src.categorizador import normalizar_texto
from src.formatacao import texto_para_decimal


def _remover_acentos(texto: str) -> str:
    """Remove acentos/diacríticos (ex.: 'cartão' -> 'cartao') para a
    comparação de termos de transferência/pagamento de fatura funcionar
    independente de o extrato do banco acentuar ou não a descrição."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))

FORMATOS_DATA = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"]
ENCODINGS_CANDIDATOS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
DELIMITADORES_CANDIDATOS = [",", ";", "\t", "|"]


def detectar_encoding(conteudo: bytes) -> str | None:
    """Tenta decodificar os bytes com uma lista de encodings comuns, em ordem."""
    for enc in ENCODINGS_CANDIDATOS:
        try:
            conteudo.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return None


def detectar_delimitador(texto: str) -> str | None:
    """Detecta o delimitador do CSV via csv.Sniffer, com fallback por contagem."""
    amostra = texto[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters="".join(DELIMITADORES_CANDIDATOS))
        return dialeto.delimiter
    except csv.Error:
        linhas = texto.splitlines()
        primeira_linha = linhas[0] if linhas else ""
        contagens = {d: primeira_linha.count(d) for d in DELIMITADORES_CANDIDATOS}
        melhor = max(contagens, key=contagens.get)
        return melhor if contagens[melhor] > 0 else None


def detectar_cabecalho(texto: str) -> bool:
    """Tenta detectar se a primeira linha é um cabeçalho. Assume True se incerto."""
    amostra = texto[:4096]
    try:
        return csv.Sniffer().has_header(amostra)
    except csv.Error:
        return True


def parsear_data(valor: str) -> date | None:
    """Tenta interpretar uma data em formatos comuns (BR e ISO). None se inválida."""
    valor = (valor or "").strip()
    if not valor:
        return None
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def processar_linha(
    data_bruta: str,
    descricao_bruta: str,
    valor_bruto: str,
    tipo_bruto: str | None = None,
    mapeamento_tipo: dict[str, str | None] | None = None,
) -> dict:
    """Interpreta uma linha do extrato, sem tocar o banco de dados.

    Se `mapeamento_tipo` for informado, o tipo da transação vem do mapeamento
    do valor bruto da coluna de Tipo. Caso contrário, o tipo é inferido pelo
    sinal do valor (positivo -> receita, negativo -> despesa).

    Retorna um dict com: data, data_bruta, descricao, valor (absoluto,
    Decimal, ou None), valor_bruto, tipo ('receita'/'despesa'/None), status
    ('ok'/'duplicada'/'revisar'/'erro') e mensagem legível.
    """
    descricao = (descricao_bruta or "").strip()
    data_parsed = parsear_data(data_bruta)
    try:
        valor_parsed = texto_para_decimal(valor_bruto)
    except ValueError:
        valor_parsed = None

    status = "ok"
    mensagem = "Válida"
    tipo = None
    valor_abs = None

    if data_parsed is None:
        status, mensagem = "erro", "Data inválida"
    elif valor_parsed is None:
        status, mensagem = "erro", "Valor inválido"
    elif valor_parsed == 0:
        status, mensagem = "erro", "Valor zero não pode ser classificado"
    else:
        valor_abs = abs(valor_parsed)
        if mapeamento_tipo is not None:
            tipo = mapeamento_tipo.get((tipo_bruto or "").strip())
        else:
            tipo = "receita" if valor_parsed > 0 else "despesa"

        if tipo is None:
            status, mensagem = "revisar", "Não classificável como receita ou despesa"

    return {
        "data": data_parsed,
        "data_bruta": data_bruta,
        "descricao": descricao,
        "valor": valor_abs,
        "valor_bruto": valor_bruto,
        "tipo": tipo,
        "status": status,
        "mensagem": mensagem,
        "possivel_transferencia": eh_possivel_transferencia(descricao),
        "possivel_pagamento_fatura": eh_possivel_pagamento_fatura(descricao),
    }


def chave_duplicidade(conta_id: int, data: date, tipo: str, valor, descricao: str) -> tuple:
    """Chave usada para detectar duplicidade: conta + data + tipo + valor + descrição normalizada."""
    return (conta_id, data, tipo, valor, normalizar_texto(descricao))


# ---------------------------------------------------------------------
# Detecção de possíveis transferências e pagamentos de fatura importados
# ---------------------------------------------------------------------
# Descrições de extrato/OFX com estes termos PODEM ser transferência entre
# contas próprias — mas também podem ser um pagamento ou receita comuns
# (ex.: "Pix recebido" de um cliente é receita, não transferência). Por
# isso isto nunca classifica automaticamente: só marca "possível
# transferência" na prévia, e quem decide é sempre o usuário (ver Parte 11).
_TERMOS_POSSIVEL_TRANSFERENCIA = (
    "pix recebido",
    "pix enviado",
    "transferencia recebida",
    "transferencia enviada",
    "ted recebida",
    "ted enviada",
    "doc recebido",
    "doc enviado",
    "transferencia entre contas",
)

_TERMOS_POSSIVEL_PAGAMENTO_FATURA = (
    "pagamento de fatura",
    "pagamento cartao",
    "pagamento do cartao",
    "fatura cartao",
    "pagto fatura",
    "pagto cartao",
)


def eh_possivel_transferencia(descricao: str) -> bool:
    """True quando a descrição contém um termo tipicamente usado por bancos
    para transferências (Pix, TED, DOC...). Não decide o tipo final: apenas
    sinaliza a linha na prévia para o usuário escolher."""
    descricao_normalizada = _remover_acentos(normalizar_texto(descricao))
    return any(termo in descricao_normalizada for termo in _TERMOS_POSSIVEL_TRANSFERENCIA)


def eh_possivel_pagamento_fatura(descricao: str) -> bool:
    """True quando a descrição contém um termo tipicamente usado por bancos
    para pagamento de fatura de cartão de crédito."""
    descricao_normalizada = _remover_acentos(normalizar_texto(descricao))
    return any(termo in descricao_normalizada for termo in _TERMOS_POSSIVEL_PAGAMENTO_FATURA)


def resolver_contas_transferencia(
    tipo_original: str, conta_extrato_id: int, outra_conta_id: int
) -> tuple[int, int]:
    """Decide (conta_id, conta_destino_id) de uma linha importada
    reclassificada como transferência, respeitando a direção do
    lançamento original no extrato — nunca assume que a conta do extrato
    é sempre a origem:

    - despesa/saída: o dinheiro SAI da conta do extrato -> ela é a origem
      (conta_id) e a outra conta é o destino.
    - receita/entrada: o dinheiro ENTRA na conta do extrato -> a outra
      conta é a origem (conta_id) e a conta do extrato é o destino.

    tipo_original é sempre 'receita' ou 'despesa' (o tipo inferido pelo
    sinal do valor antes da reclassificação; 'transferencia' nunca é um
    tipo de origem aqui).
    """
    if tipo_original == "receita":
        return outra_conta_id, conta_extrato_id
    return conta_extrato_id, outra_conta_id
