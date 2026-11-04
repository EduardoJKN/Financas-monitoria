"""Compromissos financeiros já conhecidos nos próximos meses (Parte 16).

IMPORTANTE: isto NUNCA é uma previsão garantida — é a soma do que já está
efetivamente comprometido: parcelas já lançadas com data futura,
recorrências ativas projetadas a partir da configuração atual, e faturas
de cartão já existentes com saldo devedor. Não fabrica gasto futuro
desconhecido (ex.: compras de cartão ainda não feitas). Por isso sempre
rotulado como "compromissos previstos", nunca "previsão"."""

from datetime import date
from decimal import Decimal

from src import faturas as faturas_modulo
from src import recorrencias as recorrencias_modulo
from src import transacoes as transacoes_modulo
from src.datas import avancar_meses


def _mes(d: date) -> date:
    return d.replace(day=1)


def compromissos_previstos(meses: int = 4, referencia: date | None = None) -> list[dict]:
    """Para cada um dos próximos `meses` (incluindo o mês atual): soma de
    parcelas já lançadas, recorrências ativas projetadas e faturas de
    cartão já existentes com saldo devedor, agrupadas pelo mês em que
    impactam o caixa (data da parcela / data projetada / vencimento da
    fatura)."""
    referencia = referencia or date.today()
    mes_atual = _mes(referencia)
    meses_alvo = [avancar_meses(mes_atual, i) for i in range(meses)]
    acumulado = {
        m: {"parcelas": Decimal("0"), "recorrencias": Decimal("0"), "faturas": Decimal("0")}
        for m in meses_alvo
    }

    limite = avancar_meses(mes_atual, meses)
    parcelas = transacoes_modulo.listar_transacoes(
        data_inicial=referencia, data_final=limite, limit=1000
    )
    for lancamento in parcelas:
        if lancamento.get("numero_parcela") is None:
            continue
        mes_lancamento = _mes(lancamento["data_transacao"])
        if mes_lancamento in acumulado:
            acumulado[mes_lancamento]["parcelas"] += lancamento["valor"]

    # Cobertura generosa para periodicidade semanal (~4.3 ocorrências/mês);
    # o filtro "if mes_projetado in acumulado" descarta o excedente.
    quantidade_projecao = meses * 5 + 2
    for recorrencia in recorrencias_modulo.listar_recorrencias(incluir_inativas=False):
        for data_projetada in recorrencias_modulo.projetar_proximas_ocorrencias(
            recorrencia["id"], quantidade=quantidade_projecao
        ):
            mes_projetado = _mes(data_projetada)
            if mes_projetado in acumulado:
                acumulado[mes_projetado]["recorrencias"] += recorrencia["valor"]

    for fatura in faturas_modulo.listar_faturas():
        mes_vencimento = _mes(fatura["data_vencimento"])
        if mes_vencimento not in acumulado:
            continue
        saldo_devedor = faturas_modulo.calcular_saldo_devedor_fatura(fatura["id"])
        if saldo_devedor > 0:
            acumulado[mes_vencimento]["faturas"] += saldo_devedor

    return [
        {
            "mes": mes,
            "parcelas_previstas": acumulado[mes]["parcelas"],
            "recorrencias_previstas": acumulado[mes]["recorrencias"],
            "faturas_conhecidas": acumulado[mes]["faturas"],
            "total_previsto": (
                acumulado[mes]["parcelas"]
                + acumulado[mes]["recorrencias"]
                + acumulado[mes]["faturas"]
            ),
        }
        for mes in meses_alvo
    ]
