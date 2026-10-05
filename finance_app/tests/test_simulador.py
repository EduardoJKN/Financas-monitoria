from decimal import Decimal

import pytest

from src import simulador


def test_cenario_a_10000_para_30000_aporte_2000_e_10_meses():
    resultado = simulador.calcular_meses_para_meta(
        Decimal("10000"), Decimal("30000"), Decimal("2000")
    )
    assert resultado["meses"] == 10
    assert resultado["anos"] == 0
    assert resultado["meses_restantes"] == 10
    assert resultado["ja_atingida"] is False


def test_cenario_a_arredonda_para_cima():
    resultado = simulador.calcular_meses_para_meta(
        Decimal("0"), Decimal("1000"), Decimal("300")
    )
    assert resultado["meses"] == 4  # 1000/300 = 3.33... -> arredonda para 4


def test_cenario_a_valor_atual_ja_acima_do_alvo():
    resultado = simulador.calcular_meses_para_meta(
        Decimal("35000"), Decimal("30000"), Decimal("2000")
    )
    assert resultado["ja_atingida"] is True
    assert resultado["meses"] == 0


def test_cenario_a_aporte_zero_levanta_erro_quando_meta_nao_atingida():
    with pytest.raises(ValueError):
        simulador.calcular_meses_para_meta(Decimal("10000"), Decimal("30000"), Decimal("0"))


def test_cenario_a_valores_negativos_levantam_erro():
    with pytest.raises(ValueError):
        simulador.calcular_meses_para_meta(Decimal("-1"), Decimal("30000"), Decimal("2000"))


def test_cenario_b_aporte_necessario_2000_por_mes():
    resultado = simulador.calcular_aporte_necessario(Decimal("10000"), Decimal("30000"), 10)
    assert resultado["aporte_mensal"] == Decimal("2000.00")
    assert resultado["ja_atingida"] is False
    assert isinstance(resultado["aporte_mensal"], Decimal)


def test_cenario_b_meta_ja_atingida():
    resultado = simulador.calcular_aporte_necessario(Decimal("35000"), Decimal("30000"), 10)
    assert resultado["ja_atingida"] is True
    assert resultado["aporte_mensal"] == Decimal("0")


def test_cenario_b_meses_zero_levanta_erro():
    with pytest.raises(ValueError):
        simulador.calcular_aporte_necessario(Decimal("10000"), Decimal("30000"), 0)


def test_cenario_b_meses_negativo_levanta_erro():
    with pytest.raises(ValueError):
        simulador.calcular_aporte_necessario(Decimal("10000"), Decimal("30000"), -5)


def test_cenario_c_projecao_de_saldo():
    resultado = simulador.projetar_saldo(Decimal("1000"), Decimal("500"), 3)
    assert resultado["saldo_final"] == Decimal("2500")
    assert [e["saldo"] for e in resultado["evolucao"]] == [
        Decimal("1500"),
        Decimal("2000"),
        Decimal("2500"),
    ]
    assert len(resultado["evolucao"]) == 3


def test_cenario_c_aporte_zero_mantem_saldo():
    resultado = simulador.projetar_saldo(Decimal("1000"), Decimal("0"), 3)
    assert resultado["saldo_final"] == Decimal("1000")


def test_cenario_c_meses_zero_levanta_erro():
    with pytest.raises(ValueError):
        simulador.projetar_saldo(Decimal("1000"), Decimal("500"), 0)


def test_cenario_c_saldo_inicial_negativo_levanta_erro():
    with pytest.raises(ValueError):
        simulador.projetar_saldo(Decimal("-1"), Decimal("500"), 3)


def test_todos_os_valores_retornados_sao_decimal():
    resultado = simulador.projetar_saldo(Decimal("1000"), Decimal("500"), 2)
    assert isinstance(resultado["saldo_final"], Decimal)
    assert all(isinstance(e["saldo"], Decimal) for e in resultado["evolucao"])
