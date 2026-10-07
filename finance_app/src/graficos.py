"""Gráficos reutilizáveis com Plotly.

Foco em visualizações úteis para decisão, não decorativas: ranking (barras
horizontais, Top N + Outros para nunca poluir com dezenas de categorias),
evolução temporal (linhas) e comparação entre períodos (barras agrupadas).
Valores em R$ 1.234,56 e datas em dd/mm/aaaa em todos os eixos/tooltips.
"""

from decimal import Decimal

import plotly.graph_objects as go

from src.formatacao import formatar_moeda

TOP_N_PADRAO = 8


def _agrupar_top_n(dados: list[dict], top_n: int, chave_rotulo: str, chave_valor: str) -> list[dict]:
    """Top N itens (por valor) + um item "Outros" somando o restante.
    Evita gráficos ilegíveis com muitas categorias."""
    ordenados = sorted(dados, key=lambda item: item[chave_valor], reverse=True)
    if len(ordenados) <= top_n:
        return ordenados
    principais = ordenados[:top_n]
    resto = ordenados[top_n:]
    soma_resto = sum((item[chave_valor] for item in resto), Decimal("0"))
    principais.append({chave_rotulo: "Outros", chave_valor: soma_resto})
    return principais


def grafico_vazio(titulo: str = "Sem dados") -> go.Figure:
    """Retorna um gráfico vazio como placeholder."""
    fig = go.Figure()
    fig.update_layout(title=titulo, template="plotly_dark")
    return fig


def grafico_saldos_por_conta(saldos: list[dict]) -> go.Figure:
    """Barras com o saldo atual de cada conta."""
    if not saldos:
        return grafico_vazio("Saldos por conta")

    nomes = [item["nome"] for item in saldos]
    valores = [float(item["saldo"]) for item in saldos]

    fig = go.Figure(go.Bar(x=nomes, y=valores))
    fig.update_layout(title="Saldos por conta", template="plotly_dark")
    return fig


def grafico_despesas_por_categoria(dados: list[dict]) -> go.Figure:
    """Barras horizontais com o total de despesas por categoria no período."""
    if not dados:
        return grafico_vazio("Despesas por categoria")

    categorias = [item["categoria"] for item in dados]
    valores = [float(item["total"]) for item in dados]

    fig = go.Figure(go.Bar(x=valores, y=categorias, orientation="h"))
    fig.update_layout(
        title="Despesas por categoria",
        template="plotly_dark",
        yaxis=dict(autorange="reversed"),
    )
    return fig


def grafico_evolucao_mensal(dados: list[dict]) -> go.Figure:
    """Barras agrupadas de receitas e despesas por mês no período."""
    if not dados:
        return grafico_vazio("Evolução mensal")

    meses = [item["mes"].strftime("%m/%Y") for item in dados]
    receitas = [float(item["total_receitas"]) for item in dados]
    despesas = [float(item["total_despesas"]) for item in dados]

    fig = go.Figure()
    fig.add_bar(
        name="Receitas", x=meses, y=receitas, marker_color="#2ecc71",
        hovertext=[formatar_moeda(item["total_receitas"]) for item in dados],
    )
    fig.add_bar(
        name="Despesas", x=meses, y=despesas, marker_color="#e74c3c",
        hovertext=[formatar_moeda(item["total_despesas"]) for item in dados],
    )
    fig.update_layout(title="Evolução mensal", template="plotly_dark", barmode="group")
    return fig


def grafico_ranking_categorias(
    dados: list[dict], titulo: str, top_n: int = TOP_N_PADRAO, cor: str = "#3498db"
) -> go.Figure:
    """Barras horizontais com o ranking de categorias (receita OU despesa),
    limitado a Top N + "Outros" para nunca ficar ilegível. `dados` é uma
    lista de dicts com as chaves "categoria" e "total" (ex.: saída de
    analise_financeira.receitas_por_categoria/despesas_por_categoria)."""
    if not dados:
        return grafico_vazio(titulo)

    agrupado = _agrupar_top_n(dados, top_n, "categoria", "total")
    categorias_lista = [item["categoria"] for item in agrupado]
    valores = [float(item["total"]) for item in agrupado]
    textos = [formatar_moeda(item["total"]) for item in agrupado]

    fig = go.Figure(go.Bar(x=valores, y=categorias_lista, orientation="h", marker_color=cor, text=textos))
    fig.update_layout(
        title=titulo,
        template="plotly_dark",
        yaxis=dict(autorange="reversed"),
    )
    return fig


def grafico_comparativo_periodos(
    rotulo_atual: str, valor_atual: Decimal, rotulo_anterior: str, valor_anterior: Decimal, titulo: str
) -> go.Figure:
    """Barras comparando um valor no período atual vs. no período anterior
    (ex.: despesas de uma categoria este mês vs. mês passado)."""
    fig = go.Figure(
        go.Bar(
            x=[rotulo_anterior, rotulo_atual],
            y=[float(valor_anterior), float(valor_atual)],
            marker_color=["#7f8c8d", "#3498db"],
            text=[formatar_moeda(valor_anterior), formatar_moeda(valor_atual)],
        )
    )
    fig.update_layout(title=titulo, template="plotly_dark")
    return fig


def grafico_evolucao_categoria(serie: list[dict], titulo: str) -> go.Figure:
    """Linha com a evolução mensal de uma categoria. `serie` é uma lista de
    dicts com as chaves "mes" (date) e "valor" (Decimal), em ordem
    cronológica — ex.: saída de analise_financeira.evolucao_mensal_categoria."""
    if not serie:
        return grafico_vazio(titulo)

    meses = [item["mes"].strftime("%m/%Y") for item in serie]
    valores = [float(item["valor"]) for item in serie]
    textos = [formatar_moeda(item["valor"]) for item in serie]

    fig = go.Figure(go.Scatter(x=meses, y=valores, mode="lines+markers", text=textos, line=dict(color="#3498db")))
    fig.update_layout(title=titulo, template="plotly_dark")
    return fig
