"""Gráficos reutilizáveis com Plotly."""

import plotly.graph_objects as go


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
    fig.add_bar(name="Receitas", x=meses, y=receitas)
    fig.add_bar(name="Despesas", x=meses, y=despesas)
    fig.update_layout(title="Evolução mensal", template="plotly_dark", barmode="group")
    return fig
