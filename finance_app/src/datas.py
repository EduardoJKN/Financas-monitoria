"""Funções puras de aritmética de datas.

Reutilizadas por parcelamentos, recorrências e faturas de cartão — todas
precisam avançar datas mês a mês (ou ano a ano) tratando corretamente finais
de mês (ex.: 31/01 + 1 mês -> 28/02 ou 29/02, nunca 03/03).
"""

import calendar
from datetime import date


def dia_valido_no_mes(ano: int, mes: int, dia: int) -> int:
    """Ajusta `dia` para um dia válido do mês informado (ex.: dia 31 em
    fevereiro vira 28 ou 29, conforme o ano)."""
    ultimo_dia_do_mes = calendar.monthrange(ano, mes)[1]
    return min(dia, ultimo_dia_do_mes)


def avancar_meses(data_base: date, quantidade_meses: int) -> date:
    """Avança `quantidade_meses` a partir de data_base, mantendo o dia quando
    possível e ajustando para o último dia do mês de destino quando necessário.
    """
    mes_total = data_base.month - 1 + quantidade_meses
    ano = data_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = dia_valido_no_mes(ano, mes, data_base.day)
    return date(ano, mes, dia)


def avancar_anos(data_base: date, quantidade_anos: int) -> date:
    """Avança `quantidade_anos` a partir de data_base (trata 29/02 em anos
    não bissextos)."""
    ano = data_base.year + quantidade_anos
    dia = dia_valido_no_mes(ano, data_base.month, data_base.day)
    return date(ano, data_base.month, dia)
