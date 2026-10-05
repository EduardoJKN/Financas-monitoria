"""Simulações financeiras: funções puras, sem acesso a banco ou interface.

Primeira versão: sem rendimento/juros, apenas aportes constantes.
"""

from decimal import ROUND_CEILING, Decimal


def _validar_decimal_nao_negativo(valor: Decimal, nome_campo: str) -> None:
    if not isinstance(valor, Decimal):
        raise ValueError(f"{nome_campo} deve ser do tipo Decimal.")
    if valor < 0:
        raise ValueError(f"{nome_campo} não pode ser negativo.")


def _validar_meses(meses: int) -> None:
    if not isinstance(meses, int) or isinstance(meses, bool) or meses <= 0:
        raise ValueError("meses deve ser um número inteiro maior que zero.")


def calcular_meses_para_meta(
    valor_atual: Decimal, valor_alvo: Decimal, aporte_mensal: Decimal
) -> dict:
    """A. Quanto tempo (em meses) para atingir uma meta, sem rendimento."""
    _validar_decimal_nao_negativo(valor_atual, "valor_atual")
    _validar_decimal_nao_negativo(valor_alvo, "valor_alvo")
    _validar_decimal_nao_negativo(aporte_mensal, "aporte_mensal")

    if valor_atual >= valor_alvo:
        return {"meses": 0, "anos": 0, "meses_restantes": 0, "ja_atingida": True}

    if aporte_mensal <= 0:
        raise ValueError(
            "aporte_mensal deve ser maior que zero para calcular o tempo necessário."
        )

    faltante = valor_alvo - valor_atual
    quociente = faltante / aporte_mensal
    meses_inteiros = int(quociente)
    meses = meses_inteiros + 1 if Decimal(meses_inteiros) < quociente else meses_inteiros

    anos, meses_restantes = divmod(meses, 12)
    return {
        "meses": meses,
        "anos": anos,
        "meses_restantes": meses_restantes,
        "ja_atingida": False,
    }


def calcular_aporte_necessario(valor_atual: Decimal, valor_alvo: Decimal, meses: int) -> dict:
    """B. Quanto aportar por mês para atingir a meta em uma quantidade de meses."""
    _validar_decimal_nao_negativo(valor_atual, "valor_atual")
    _validar_decimal_nao_negativo(valor_alvo, "valor_alvo")
    _validar_meses(meses)

    if valor_atual >= valor_alvo:
        return {"aporte_mensal": Decimal("0"), "ja_atingida": True}

    faltante = valor_alvo - valor_atual
    aporte_mensal = (faltante / Decimal(meses)).quantize(
        Decimal("0.01"), rounding=ROUND_CEILING
    )
    return {"aporte_mensal": aporte_mensal, "ja_atingida": False}


def projetar_saldo(saldo_inicial: Decimal, aporte_mensal: Decimal, meses: int) -> dict:
    """C. Projeta o saldo mês a mês com aportes constantes, sem rendimento."""
    _validar_decimal_nao_negativo(saldo_inicial, "saldo_inicial")
    _validar_decimal_nao_negativo(aporte_mensal, "aporte_mensal")
    _validar_meses(meses)

    evolucao = []
    saldo = saldo_inicial
    for mes in range(1, meses + 1):
        saldo = saldo + aporte_mensal
        evolucao.append({"mes": mes, "saldo": saldo})

    return {"saldo_final": saldo, "evolucao": evolucao}
