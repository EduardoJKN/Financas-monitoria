"""Lógica pura (sem I/O de banco) para importação de extratos CSV.

Mantido separado da página Streamlit para ser testável diretamente:
detecção de encoding/delimitador/cabeçalho, parsing de data e classificação
de cada linha em receita/despesa/erro/revisão.
"""

import csv
from datetime import date, datetime

from src.categorizador import normalizar_texto
from src.formatacao import texto_para_decimal

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
    }


def chave_duplicidade(conta_id: int, data: date, tipo: str, valor, descricao: str) -> tuple:
    """Chave usada para detectar duplicidade: conta + data + tipo + valor + descrição normalizada."""
    return (conta_id, data, tipo, valor, normalizar_texto(descricao))
