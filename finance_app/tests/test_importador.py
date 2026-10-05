from datetime import date

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
