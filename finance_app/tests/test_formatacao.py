from decimal import Decimal

import pytest

from src.formatacao import formatar_moeda, texto_para_decimal


def test_formatar_moeda_positivo():
    assert formatar_moeda(Decimal("1234.56")) == "R$ 1.234,56"


def test_formatar_moeda_negativo():
    assert formatar_moeda(Decimal("-1234.56")) == "-R$ 1.234,56"


def test_formatar_moeda_zero():
    assert formatar_moeda(Decimal("0")) == "R$ 0,00"


def test_texto_para_decimal_internacional():
    assert texto_para_decimal("1234.56") == Decimal("1234.56")


def test_texto_para_decimal_brasileiro():
    assert texto_para_decimal("1.234,56") == Decimal("1234.56")


def test_texto_para_decimal_negativo():
    assert texto_para_decimal("-85,90") == Decimal("-85.90")


def test_texto_para_decimal_com_prefixo_moeda():
    assert texto_para_decimal("R$ 1.234,56") == Decimal("1234.56")


def test_texto_para_decimal_parenteses_negativo():
    assert texto_para_decimal("(85,90)") == Decimal("-85.90")


def test_texto_para_decimal_vazio_levanta_erro():
    with pytest.raises(ValueError):
        texto_para_decimal("")


def test_texto_para_decimal_invalido_levanta_erro():
    with pytest.raises(ValueError):
        texto_para_decimal("abc")


def test_texto_para_decimal_nunca_usa_float():
    # 0.1 + 0.2 != 0.3 em float; a conversão via string deve ser exata
    resultado = texto_para_decimal("0,30")
    assert resultado == Decimal("0.30")
    assert resultado != Decimal(0.1) + Decimal(0.2)
