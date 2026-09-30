"""Gráficos reutilizáveis com Plotly."""

import plotly.graph_objects as go


def grafico_vazio(titulo: str = "Sem dados") -> go.Figure:
    """Retorna um gráfico vazio como placeholder."""
    fig = go.Figure()
    fig.update_layout(title=titulo, template="plotly_dark")
    return fig
