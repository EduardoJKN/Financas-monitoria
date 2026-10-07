from datetime import date

import streamlit as st

from src import analise_financeira as af
from src import resumo_financeiro as resumo
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import formatar_moeda
from src.graficos import (
    grafico_evolucao_categoria,
    grafico_evolucao_mensal,
    grafico_ranking_categorias,
    grafico_saldos_por_conta,
)

st.title("Visão Geral")

OPCOES_PERIODO = {
    "Este mês": "este_mes",
    "Mês passado": "mes_passado",
    "Últimos 30 dias": "ultimos_30_dias",
    "Últimos 3 meses": "ultimos_3_meses",
    "Últimos 6 meses": "ultimos_6_meses",
    "Este ano": "este_ano",
    "Personalizado": "personalizado",
}

rotulo_periodo = st.selectbox("Período", list(OPCOES_PERIODO.keys()), index=0, key="vg_periodo")
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
    receitas_categoria = af.receitas_por_categoria(data_inicial, data_final)
    despesas_categoria = af.despesas_por_categoria(data_inicial, data_final)
    evolucao_mensal = resumo.resumir_por_mes(data_inicial, data_final)
    indicadores_cartoes = resumo.calcular_indicadores_cartoes()
    taxa_periodo = af.taxa_economia_periodo(data_inicial, data_final)
    projecao = af.projetar_gasto_mes()
    insights = af.gerar_insights()
except (ValueError, ErroBancoDeDados) as exc:
    st.error(str(exc))
    st.stop()

aba_resumo, aba_categorias, aba_tendencias, aba_insights = st.tabs(
    ["Resumo", "Categorias", "Tendências", "Insights"]
)

# =======================================================================
# Resumo
# =======================================================================
with aba_resumo:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saldo total atual", formatar_moeda(saldo_total))
    col2.metric("🟢 Receitas do período", formatar_moeda(resumo_periodo["total_receitas"]))
    col3.metric("🔴 Despesas do período", formatar_moeda(resumo_periodo["total_despesas"]))
    col4.metric("Resultado do período", formatar_moeda(resumo_periodo["resultado"]))

    col5, col6 = st.columns(2)
    with col5:
        if taxa_periodo["taxa"] is not None:
            st.metric("Taxa de economia (período selecionado)", f"{taxa_periodo['taxa']:.1f}%".replace(".", ","))
        else:
            st.metric("Taxa de economia (período selecionado)", "—")
    with col6:
        rotulo_projecao = "Gasto projetado até o fim do mês"
        if projecao["confianca_baixa"]:
            rotulo_projecao += " (baixa confiança: poucos dias no mês)"
        st.metric(rotulo_projecao, formatar_moeda(projecao["projecao_fim_mes"]))
        st.caption(
            f"Baseado em {formatar_moeda(projecao['despesas_acumuladas'])} gastos em "
            f"{projecao['dias_decorridos']} de {projecao['dias_do_mes']} dias do mês. "
            f"Mês passado: {formatar_moeda(projecao['mes_passado_total'])} · "
            f"Média 3 meses: {formatar_moeda(projecao['media_3_meses'])}."
        )

    st.divider()
    st.subheader("Saldos por conta")
    if not saldos_contas:
        st.info("Nenhuma conta cadastrada ainda. Cadastre uma conta na página Contas.")
    else:
        st.plotly_chart(grafico_saldos_por_conta(saldos_contas), use_container_width=True)
        sem_conciliacao = [c["nome"] for c in saldos_contas if c.get("data_saldo_inicial") is None]
        if sem_conciliacao:
            st.caption(
                "⚠️ Ainda precisam de conciliação: " + ", ".join(sem_conciliacao) +
                " — veja a página Contas."
            )

    if indicadores_cartoes["cartoes"]:
        st.divider()
        st.subheader("Cartões de crédito")
        col_c1, col_c2 = st.columns(2)
        col_c1.metric("Faturas abertas", indicadores_cartoes["total_faturas_abertas"])
        col_c2.metric("Faturas a vencer", indicadores_cartoes["total_faturas_a_vencer"])
        for info in indicadores_cartoes["cartoes"]:
            st.write(
                f"**{info['nome']}** — limite {formatar_moeda(info['limite'])} · "
                f"utilizado {formatar_moeda(info['limite_utilizado'])} · "
                f"disponível {formatar_moeda(info['limite_disponivel'])}"
            )

# =======================================================================
# Categorias
# =======================================================================
with aba_categorias:
    col_r, col_d = st.columns(2)
    with col_r:
        st.subheader("Maiores receitas")
        if not receitas_categoria:
            st.info("Nenhuma receita no período selecionado.")
        else:
            st.plotly_chart(
                grafico_ranking_categorias(receitas_categoria, "Receitas por categoria", cor="#2ecc71"),
                use_container_width=True,
            )
            maior = receitas_categoria[0]
            st.caption(
                f"Maior fonte de receita: **{maior['categoria']}** "
                f"({formatar_moeda(maior['total'])}, {maior['percentual']:.1f}%)".replace(".", ",")
            )
    with col_d:
        st.subheader("Maiores despesas")
        if not despesas_categoria:
            st.info("Nenhuma despesa no período selecionado.")
        else:
            st.plotly_chart(
                grafico_ranking_categorias(despesas_categoria, "Despesas por categoria", cor="#e74c3c"),
                use_container_width=True,
            )
            maior = despesas_categoria[0]
            st.caption(
                f"Categoria com maior gasto: **{maior['categoria']}** "
                f"({formatar_moeda(maior['total'])}, {maior['percentual']:.1f}%)".replace(".", ",")
            )

# =======================================================================
# Tendências
# =======================================================================
with aba_tendencias:
    st.subheader("Evolução mensal (receitas x despesas)")
    if not evolucao_mensal:
        st.info("Sem dados suficientes para exibir a evolução mensal no período selecionado.")
    else:
        st.plotly_chart(grafico_evolucao_mensal(evolucao_mensal), use_container_width=True)

    st.subheader("Comparação histórica por categoria")
    categorias_disponiveis = despesas_categoria + receitas_categoria
    if not categorias_disponiveis:
        st.info("Sem categorias com movimentação no período para comparar.")
    else:
        opcoes = [(c["categoria"], c["categoria_id"], c["tipo"]) for c in categorias_disponiveis]
        rotulo_escolhido = st.selectbox(
            "Categoria", [o[0] for o in opcoes], key="vg_categoria_tendencia"
        )
        _, categoria_id_escolhida, tipo_escolhido = next(o for o in opcoes if o[0] == rotulo_escolhido)

        comparacao = af.comparar_categoria_historico(categoria_id_escolhida, tipo_escolhido)
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Este mês", formatar_moeda(comparacao["este_mes"]))
        col_t2.metric("Mês passado", formatar_moeda(comparacao["mes_passado"]))
        col_t3.metric("Média 3 meses", formatar_moeda(comparacao["media_3_meses"]))
        if comparacao["variacao_vs_media_percentual"] is not None:
            st.caption(
                f"Variação deste mês vs média: "
                f"{comparacao['variacao_vs_media_percentual']:+.1f}%".replace(".", ",")
            )

        serie = af.evolucao_mensal_categoria(categoria_id_escolhida, tipo_escolhido, meses=6)
        st.plotly_chart(
            grafico_evolucao_categoria(serie, f"Evolução de {rotulo_escolhido}"),
            use_container_width=True,
        )
        padrao = af.detectar_padrao_consecutivo([item["valor"] for item in serie])
        if padrao == "crescimento":
            st.warning(f"{rotulo_escolhido} vem crescendo nos últimos meses.")
        elif padrao == "queda":
            st.success(f"{rotulo_escolhido} vem caindo nos últimos meses.")

# =======================================================================
# Insights
# =======================================================================
with aba_insights:
    st.caption("Baseados no mês atual, independente do período selecionado acima.")
    st.subheader("Destaques e pontos de atenção")
    if not insights:
        st.info("Nenhum insight relevante com os dados atuais.")
    else:
        for texto in insights:
            st.write(f"💡 {texto}")

    st.subheader("Gastos fora do padrão no período selecionado")
    anomalias_encontradas = []
    for linha in despesas_categoria:
        anomalias_encontradas.extend(
            af.detectar_lancamentos_fora_padrao(linha["categoria_id"], data_inicial, data_final)
        )
    if not anomalias_encontradas:
        st.caption(
            "Nenhum lançamento fora do padrão detectado (ou amostra insuficiente para "
            "a análise estatística — usamos a regra do IQR, que exige ao menos "
            f"{af.AMOSTRA_MINIMA_ANOMALIA} lançamentos na categoria no período)."
        )
    else:
        for lancamento in anomalias_encontradas:
            st.write(
                f"⚠️ {lancamento['descricao']} — {formatar_moeda(lancamento['valor'])} em "
                f"{lancamento['data_transacao'].strftime('%d/%m/%Y')}"
            )
