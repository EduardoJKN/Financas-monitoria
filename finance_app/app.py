import os

import streamlit as st

# Ponte de configuração: em produção (ex.: Streamlit Community Cloud), a
# DATABASE_URL normalmente vem de st.secrets, não de um arquivo .env. A
# camada de acesso a dados (src/banco_de_dados.py) só lê variáveis de
# ambiente (os.getenv) para continuar testável sem depender do Streamlit;
# aqui — e só aqui, no ponto de entrada do app — copiamos o secret para
# os.environ antes de qualquer módulo em src/ ser usado, se ele ainda não
# estiver definido localmente via .env.
if "DATABASE_URL" not in os.environ:
    try:
        if "DATABASE_URL" in st.secrets:
            os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
    except Exception:
        pass  # sem secrets.toml configurado (ambiente local com .env) — ok

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


def _pagina_inicio() -> None:
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
        - **Lançamentos** — registrar lançamentos, parcelamentos e recorrências
        - **Contas** — cadastrar e gerenciar contas
        - **Cartões** — cartões, faturas e pagamentos
        - **Categorias** — categorias e regras de categorização automática
        - **Importação** — importar extratos (CSV e OFX)
        - **Metas** — acompanhar objetivos financeiros
        - **Simulador** — projetar cenários
        """
    )


paginas = [
    st.Page(_pagina_inicio, title="Início", icon="🏠", default=True),
    st.Page("pages/1_Visao_Geral.py", title="Visão Geral", icon="📊"),
    st.Page("pages/2_Lancamentos.py", title="Lançamentos", icon="📝"),
    st.Page("pages/3_Contas.py", title="Contas", icon="🏦"),
    st.Page("pages/8_Cartoes.py", title="Cartões", icon="💳"),
    st.Page("pages/4_Categorias.py", title="Categorias", icon="🏷️"),
    st.Page("pages/5_Importacao.py", title="Importação", icon="📥"),
    st.Page("pages/6_Metas.py", title="Metas", icon="🎯"),
    st.Page("pages/7_Simulador.py", title="Simulador", icon="🧮"),
]

st.navigation(paginas).run()
