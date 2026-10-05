from datetime import date

import streamlit as st

from src import resumo_financeiro as resumo
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import formatar_moeda
from src.graficos import (
    grafico_despesas_por_categoria,
    grafico_evolucao_mensal,
    grafico_saldos_por_conta,
)

st.set_page_config(page_title="Visão Geral | Economia UaU", layout="wide")
st.title("Visão Geral")

OPCOES_PERIODO = {
    "Este mês": "este_mes",
    "Mês passado": "mes_passado",
    "Últimos 30 dias": "ultimos_30_dias",
    "Este ano": "este_ano",
    "Personalizado": "personalizado",
}

rotulo_periodo = st.selectbox(
    "Período", list(OPCOES_PERIODO.keys()), index=0, key="vg_periodo"
)
periodo = OPCOES_PERIODO[rotulo_periodo]

if periodo == "personalizado":
    col_ini, col_fim = st.columns(2)
    with col_ini:
        data_inicial = st.date_input(
            "Data inicial", value=date.today().replace(day=1), key="vg_data_inicial"
        )
    with col_fim:
        data_final = st.date_input("Data final", value=date.today(), key="vg_data_final")
    if data_inicial > data_final:
        st.error("A data inicial não pode ser posterior à data final.")
        st.stop()
else:
    data_inicial, data_final = resumo.calcular_intervalo_periodo(periodo)

try:
    saldo_total = resumo.calcular_saldo_total()
    saldos_contas = resumo.calcular_saldos_contas()
    resumo_periodo = resumo.calcular_resumo_periodo(data_inicial, data_final)
    despesas_categoria = resumo.resumir_por_categoria(
        data_inicial, data_final, tipo="despesa"
    )
    evolucao_mensal = resumo.resumir_por_mes(data_inicial, data_final)
except (ValueError, ErroBancoDeDados) as exc:
    st.error(str(exc))
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Saldo total atual", formatar_moeda(saldo_total))
col2.metric("Receitas do período", formatar_moeda(resumo_periodo["total_receitas"]))
col3.metric("Despesas do período", formatar_moeda(resumo_periodo["total_despesas"]))
col4.metric("Resultado do período", formatar_moeda(resumo_periodo["resultado"]))

st.divider()
st.subheader("Saldos por conta")
if not saldos_contas:
    st.info("Nenhuma conta cadastrada ainda. Cadastre uma conta na página Contas.")
else:
    st.plotly_chart(grafico_saldos_por_conta(saldos_contas), use_container_width=True)
    for item in saldos_contas:
        rotulo = item["nome"] if item["ativa"] else f"{item['nome']} (inativa)"
        st.write(f"**{rotulo}:** {formatar_moeda(item['saldo'])}")

st.subheader("Despesas por categoria")
if not despesas_categoria:
    st.info("Nenhuma despesa registrada no período selecionado.")
else:
    st.plotly_chart(
        grafico_despesas_por_categoria(despesas_categoria), use_container_width=True
    )

st.subheader("Evolução mensal")
if not evolucao_mensal:
    st.info("Sem dados suficientes para exibir a evolução mensal no período selecionado.")
else:
    st.plotly_chart(grafico_evolucao_mensal(evolucao_mensal), use_container_width=True)
