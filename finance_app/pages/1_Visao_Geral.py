import streamlit as st

from src.graficos import grafico_vazio

st.set_page_config(page_title="Visão Geral | Economia UaU", layout="wide")

st.title("Visão Geral")
st.info("Visão geral em construção.")

st.plotly_chart(grafico_vazio("Resumo financeiro"), use_container_width=True)
