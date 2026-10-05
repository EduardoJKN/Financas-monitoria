import streamlit as st

from src.banco_de_dados import testar_conexao

st.set_page_config(
    page_title="Economia UaU",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Economia UaU")
st.caption("Organização financeira pessoal")

if testar_conexao():
    st.success("Conexão com o banco de dados: OK")
else:
    st.error(
        "Conexão com o banco de dados: falhou. "
        "Verifique o arquivo .env e a variável DATABASE_URL."
    )

st.markdown(
    """
    Use o menu lateral para navegar entre as páginas:

    - **Visão Geral** — visão geral das finanças
    - **Lançamentos** — registrar e consultar transações
    - **Contas** — cadastrar e gerenciar contas
    - **Categorias** — cadastrar e gerenciar categorias
    - **Importação** — importar extratos e arquivos
    - **Metas** — acompanhar objetivos financeiros
    - **Simulador** — projetar cenários
    """
)
