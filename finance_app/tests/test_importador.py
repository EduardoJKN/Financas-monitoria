from datetime import date

import pytest

from src import importador


def test_detectar_encoding_utf8():
    conteudo = "Data,Descricao,Valor\n01/10/2026,Teste,100\n".encode("utf-8")
    assert importador.detectar_encoding(conteudo) in ("utf-8-sig", "utf-8")


def test_detectar_encoding_latin1():
    conteudo = "Data,Descricao,Valor\n01/10/2026,Café,100\n".encode("latin1")
    encoding = importador.detectar_encoding(conteudo)
    assert encoding in ("cp1252", "latin1")


def test_detectar_delimitador_virgula():
    texto = "Data,Descricao,Valor\n01/10/2026,Teste,100\n"
    assert importador.detectar_delimitador(texto) == ","


def test_detectar_delimitador_ponto_e_virgula():
    texto = "Data;Descricao;Valor\n01/10/2026;Teste;100\n"
    assert importador.detectar_delimitador(texto) == ";"


def test_detectar_cabecalho_true():
    texto = "Data;Descricao;Valor\n01/10/2026;Teste;100\n"
    assert importador.detectar_cabecalho(texto) is True


def test_parsear_data_formatos_validos():
    assert importador.parsear_data("01/10/2026") == date(2026, 10, 1)
    assert importador.parsear_data("2026-10-01") == date(2026, 10, 1)


def test_parsear_data_invalida():
    assert importador.parsear_data("31/02/2026") is None
    assert importador.parsear_data("") is None


def test_processar_linha_decimal_internacional():
    linha = importador.processar_linha("01/10/2026", "Teste Intl", "1234.56")
    assert str(linha["valor"]) == "1234.56"
    assert linha["tipo"] == "receita"
    assert linha["status"] == "ok"


def test_processar_linha_decimal_brasileiro():
    linha = importador.processar_linha("01/10/2026", "Teste BR", "1.234,56")
    assert str(linha["valor"]) == "1234.56"


def test_processar_linha_negativo_vira_despesa():
    linha = importador.processar_linha("01/10/2026", "Teste Negativo", "-85,90")
    assert str(linha["valor"]) == "85.90"
    assert linha["tipo"] == "despesa"


def test_processar_linha_prefixo_moeda():
    linha = importador.processar_linha("01/10/2026", "Teste Moeda", "R$ 1.234,56")
    assert str(linha["valor"]) == "1234.56"


def test_processar_linha_data_invalida():
    linha = importador.processar_linha("31/02/2026", "Data Invalida", "10,00")
    assert linha["status"] == "erro"
    assert "Data" in linha["mensagem"]


def test_processar_linha_valor_invalido():
    linha = importador.processar_linha("01/10/2026", "Valor Invalido", "abc")
    assert linha["status"] == "erro"


def test_processar_linha_valor_zero():
    linha = importador.processar_linha("01/10/2026", "Valor Zero", "0")
    assert linha["status"] == "erro"


def test_processar_linha_tipo_mapeado_explicito():
    mapeamento = {"CREDITO": "receita", "DEBITO": "despesa", "TED": None}
    linha = importador.processar_linha(
        "01/10/2026", "Credito Mapeado", "500,00", tipo_bruto="CREDITO", mapeamento_tipo=mapeamento
    )
    assert linha["tipo"] == "receita"
    assert linha["status"] == "ok"


def test_processar_linha_tipo_mapeado_para_revisar():
    mapeamento = {"CREDITO": "receita", "DEBITO": "despesa", "TED": None}
    linha = importador.processar_linha(
        "01/10/2026", "Transferencia", "500,00", tipo_bruto="TED", mapeamento_tipo=mapeamento
    )
    assert linha["status"] == "revisar"
    assert linha["tipo"] is None


def test_chave_duplicidade_normaliza_descricao():
    chave1 = importador.chave_duplicidade(1, date(2026, 10, 1), "despesa", 45.90, "  IFOOD *delivery  ")
    chave2 = importador.chave_duplicidade(1, date(2026, 10, 1), "despesa", 45.90, "ifood *DELIVERY")
    assert chave1 == chave2


# ---------------------------------------------------------------------
# Detecção de possível transferência / pagamento de fatura — Partes 11/12
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "descricao",
    ["Pix recebido", "Pix enviado", "Transferência recebida", "TED enviada", "DOC recebido"],
)
def test_eh_possivel_transferencia_detecta_termos_comuns(descricao):
    assert importador.eh_possivel_transferencia(descricao) is True


def test_eh_possivel_transferencia_nao_marca_descricao_comum():
    assert importador.eh_possivel_transferencia("Supermercado Extra") is False


@pytest.mark.parametrize(
    "descricao",
    ["Pagamento de fatura", "Pagamento cartão", "Fatura cartão", "pagto fatura cartao nubank"],
)
def test_eh_possivel_pagamento_fatura_detecta_termos_comuns(descricao):
    assert importador.eh_possivel_pagamento_fatura(descricao) is True


def test_eh_possivel_pagamento_fatura_nao_marca_descricao_comum():
    assert importador.eh_possivel_pagamento_fatura("Restaurante Sabor Caseiro") is False


def test_processar_linha_marca_flags_de_possivel_classificacao():
    linha = importador.processar_linha("01/10/2026", "Pix recebido de Joao", "150,00")
    assert linha["possivel_transferencia"] is True
    assert linha["possivel_pagamento_fatura"] is False


# ---------------------------------------------------------------------
# Direção da transferência reclassificada na importação (correção):
# a conta do extrato não é sempre a origem — depende do sinal original.
# ---------------------------------------------------------------------
def test_resolver_contas_transferencia_despesa_extrato_e_origem():
    # "Pix enviado" (despesa/saída): dinheiro sai da conta do extrato (10)
    # para a outra conta (20).
    conta_id, conta_destino_id = importador.resolver_contas_transferencia(
        "despesa", conta_extrato_id=10, outra_conta_id=20
    )
    assert conta_id == 10
    assert conta_destino_id == 20


def test_resolver_contas_transferencia_receita_extrato_e_destino():
    # "Pix recebido" (receita/entrada): dinheiro vem da outra conta (20)
    # para a conta do extrato (10) — a conta do extrato é o DESTINO, não a
    # origem.
    conta_id, conta_destino_id = importador.resolver_contas_transferencia(
        "receita", conta_extrato_id=10, outra_conta_id=20
    )
    assert conta_id == 20
    assert conta_destino_id == 10
