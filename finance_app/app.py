import os
import time

import streamlit as st

# Ponte de configuração: em produção (ex.: Streamlit Community Cloud), estas
# variáveis normalmente vêm de st.secrets, não de um arquivo .env. A camada
# de acesso a dados e autenticação só lê variáveis de ambiente (os.getenv)
# para continuar testável sem depender do Streamlit; aqui — e só aqui, no
# ponto de entrada do app — copiamos cada secret para os.environ antes de
# qualquer módulo em src/ ser usado, se ele ainda não estiver definido
# localmente via .env.
for _chave in (
    "DATABASE_URL",
    "APP_DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "APP_URL",
):
    if _chave not in os.environ:
        try:
            if _chave in st.secrets:
                os.environ[_chave] = st.secrets[_chave]
        except Exception:
            pass  # sem secrets.toml configurado (ambiente local com .env) — ok

from src import auth
from src.banco_de_dados import ErroBancoDeDados, definir_usuario_atual, testar_conexao
from src.categorias_padrao import criar_categorias_padrao_se_necessario
from src.migracao_legado import existe_dados_legado_nao_reivindicados, reivindicar_dados_legado

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


# ---------------------------------------------------------------------
# Autenticação: nenhuma página financeira é renderizada sem sessão válida
# ---------------------------------------------------------------------
def _reenviar_confirmacao_ui(email_sugerido: str, chave_sufixo: str) -> None:
    """Bloco reutilizável de reenvio de e-mail de confirmação — aparece
    tanto reativamente (login falhou por e-mail não confirmado, cadastro
    recém-criado) quanto proativamente (usuário informa que o link
    expirou), sempre com o mesmo comportamento."""
    email_reenvio = st.text_input(
        "E-mail cadastrado", value=email_sugerido, key=f"auth_reenviar_email_{chave_sufixo}"
    )
    if st.button(
        "Reenviar e-mail de confirmação", key=f"auth_reenviar_botao_{chave_sufixo}"
    ):
        try:
            auth.reenviar_confirmacao(email_reenvio)
            st.success(
                "Se essa conta existir e ainda não estiver confirmada, "
                "enviamos um novo e-mail de confirmação."
            )
        except (ValueError, auth.ErroAutenticacao) as exc:
            st.error(str(exc))


def _tela_autenticacao() -> None:
    st.title("Economia UaU")
    st.caption("Organização financeira pessoal")

    aba_entrar, aba_criar, aba_recuperar, aba_reenviar = st.tabs(
        ["Entrar", "Criar conta", "Recuperar senha", "Reenviar confirmação"]
    )

    with aba_entrar:
        email = st.text_input("E-mail", key="auth_entrar_email")
        senha = st.text_input("Senha", type="password", key="auth_entrar_senha")
        if st.button("Entrar", type="primary", key="auth_entrar_botao"):
            try:
                resultado = auth.entrar(email, senha)
                if not resultado.get("access_token"):
                    st.info(
                        "Login quase pronto: confirme seu e-mail (verifique a caixa de "
                        "entrada) antes de entrar."
                    )
                else:
                    st.session_state["sessao"] = resultado
                    st.session_state["sessao_verificada_em"] = time.time()
                    st.rerun()
            except (ValueError, auth.ErroAutenticacao) as exc:
                st.error(str(exc))
                if auth.email_nao_confirmado(str(exc)):
                    st.info(
                        "Parece que este e-mail ainda não foi confirmado, ou o link "
                        "anterior expirou."
                    )
                    _reenviar_confirmacao_ui(email, chave_sufixo="entrar")

    with aba_criar:
        novo_email = st.text_input("E-mail", key="auth_criar_email")
        nova_senha = st.text_input("Senha (mín. 6 caracteres)", type="password", key="auth_criar_senha")
        confirmar_senha = st.text_input(
            "Confirmar senha", type="password", key="auth_criar_confirmar"
        )
        if st.button("Criar conta", type="primary", key="auth_criar_botao"):
            if nova_senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            else:
                try:
                    resultado = auth.cadastrar(novo_email, nova_senha)
                    if resultado.get("access_token"):
                        st.session_state["sessao"] = resultado
                        st.session_state["sessao_verificada_em"] = time.time()
                        st.rerun()
                    else:
                        st.session_state["auth_criar_email_confirmado_pendente"] = novo_email
                        st.success(
                            "Conta criada. Verifique seu e-mail para confirmar o cadastro "
                            "antes de entrar."
                        )
                except (ValueError, auth.ErroAutenticacao) as exc:
                    st.error(str(exc))

        email_pendente = st.session_state.get("auth_criar_email_confirmado_pendente")
        if email_pendente:
            st.caption("Não recebeu o e-mail, ou o link expirou?")
            _reenviar_confirmacao_ui(email_pendente, chave_sufixo="criar")

    with aba_recuperar:
        email_recuperar = st.text_input("E-mail cadastrado", key="auth_recuperar_email")
        if st.button("Enviar e-mail de recuperação", key="auth_recuperar_botao"):
            try:
                auth.solicitar_recuperacao_senha(email_recuperar)
                st.success(
                    "Se esse e-mail estiver cadastrado, enviamos instruções de "
                    "redefinição de senha."
                )
            except (ValueError, auth.ErroAutenticacao) as exc:
                st.error(str(exc))

    with aba_reenviar:
        st.caption(
            "Use esta opção se sua conta ainda não foi confirmada ou se o link de "
            "confirmação anterior expirou."
        )
        _reenviar_confirmacao_ui("", chave_sufixo="aba")


# ---------------------------------------------------------------------
# Validação/renovação de sessão: um access_token expirado ou revogado no
# Supabase (logout remoto, troca de senha, revogação manual) não pode
# continuar dando acesso aos dados só porque "sessao" ainda está em
# st.session_state. Revalida contra o Supabase Auth periodicamente (TTL
# curto, não a cada rerun — cada interação do Streamlit reexecuta todo o
# script) e tenta renovar via refresh_token antes de desistir. Nenhum
# token é logado/impresso em nenhum ponto deste fluxo.
# ---------------------------------------------------------------------
TTL_VALIDACAO_SESSAO_SEGUNDOS = 60

sessao = st.session_state.get("sessao")
if sessao:
    ultima_verificacao = st.session_state.get("sessao_verificada_em", 0.0)
    if time.time() - ultima_verificacao > TTL_VALIDACAO_SESSAO_SEGUNDOS:
        sessao = auth.validar_ou_renovar_sessao(sessao)
        if sessao is None:
            st.session_state.pop("sessao", None)
            st.session_state.pop("sessao_verificada_em", None)
        else:
            st.session_state["sessao"] = sessao
            st.session_state["sessao_verificada_em"] = time.time()

usuario = (sessao or {}).get("user") or {}
usuario_id = usuario.get("id")

if not sessao or not usuario_id:
    _tela_autenticacao()
    st.stop()

definir_usuario_atual(usuario_id)

try:
    criar_categorias_padrao_se_necessario()
except ErroBancoDeDados:
    pass  # não bloqueia o uso do app por conta disso

try:
    _tem_legado = existe_dados_legado_nao_reivindicados()
except ErroBancoDeDados:
    _tem_legado = False

if _tem_legado:
    with st.container(border=True):
        st.info("Encontramos dados criados antes da implementação de usuários.")
        if not st.session_state.get("confirmar_claim_legado"):
            if st.button("Associar dados existentes à minha conta", key="legado_iniciar"):
                st.session_state["confirmar_claim_legado"] = True
                st.rerun()
        else:
            st.warning(
                "Isso vai associar TODOS os dados antigos ainda sem proprietário à sua "
                "conta. Essa ação não poderá ser repetida por outra pessoa depois."
            )
            col_confirmar, col_cancelar = st.columns(2)
            with col_confirmar:
                if st.button("Confirmar associação", type="primary", key="legado_confirmar"):
                    try:
                        associou = reivindicar_dados_legado(usuario_id)
                        st.session_state["confirmar_claim_legado"] = False
                        if associou:
                            st.success("Dados associados à sua conta com sucesso.")
                        else:
                            st.warning("Esses dados já haviam sido associados a outra conta.")
                    except ErroBancoDeDados as exc:
                        st.error(str(exc))
                    st.rerun()
            with col_cancelar:
                if st.button("Cancelar", key="legado_cancelar"):
                    st.session_state["confirmar_claim_legado"] = False
                    st.rerun()


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

with st.sidebar:
    st.caption(f"Conectado como **{usuario.get('email', '—')}**")
    if st.button("Sair", key="auth_sair"):
        auth.sair(sessao.get("access_token"))
        st.session_state.pop("sessao", None)
        st.session_state.pop("sessao_verificada_em", None)
        definir_usuario_atual(None)
        st.rerun()

st.navigation(paginas).run()
