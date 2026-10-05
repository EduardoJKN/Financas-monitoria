import streamlit as st

from src import categorias
from src.banco_de_dados import ErroBancoDeDados

st.set_page_config(page_title="Categorias | Economia UaU", layout="wide")
st.title("Categorias")

TIPOS_LABEL = {"receita": "Receita", "despesa": "Despesa", "ambos": "Ambos"}
TIPOS_INTERNO = {rotulo: interno for interno, rotulo in TIPOS_LABEL.items()}

# ---------------------------------------------------------------------
# Estado da página
# ---------------------------------------------------------------------
st.session_state.setdefault("cat_editando_id", None)
st.session_state.setdefault("cat_form_versao", 0)
st.session_state.setdefault("cat_excluir_id", None)

mensagem = st.session_state.pop("cat_mensagem", None)
if mensagem:
    st.success(mensagem)


def _definir_mensagem(texto: str) -> None:
    st.session_state["cat_mensagem"] = texto


try:
    todas_categorias = categorias.listar_categorias(incluir_inativas=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

mapa_categorias = {c["id"]: c for c in todas_categorias}


def caminho_categoria(categoria_id: int | None) -> str:
    if categoria_id is None:
        return "—"
    partes = []
    visitados = set()
    atual_id = categoria_id
    while atual_id is not None and atual_id not in visitados:
        categoria = mapa_categorias.get(atual_id)
        if categoria is None:
            break
        visitados.add(atual_id)
        rotulo = (
            categoria["nome"] if categoria["ativa"] else f"{categoria['nome']} (inativa)"
        )
        partes.append(rotulo)
        atual_id = categoria["categoria_pai_id"]
    return " > ".join(reversed(partes)) if partes else "—"


# ---------------------------------------------------------------------
# Formulário de criação/edição
# ---------------------------------------------------------------------
editando_id = st.session_state["cat_editando_id"]
dados_edicao = mapa_categorias.get(editando_id) if editando_id is not None else None
if editando_id is not None and dados_edicao is None:
    st.session_state["cat_editando_id"] = None
    editando_id = None

sufixo = (
    f"edit_{editando_id}_{st.session_state['cat_form_versao']}"
    if editando_id
    else f"novo_{st.session_state['cat_form_versao']}"
)

st.subheader(f"Editar categoria #{editando_id}" if editando_id else "Nova categoria")

col_a, col_b = st.columns(2)
with col_a:
    nome = st.text_input(
        "Nome", value=dados_edicao["nome"] if dados_edicao else "", key=f"nome_{sufixo}"
    )
with col_b:
    rotulos_tipo = list(TIPOS_LABEL.values())
    tipo_default = TIPOS_LABEL[dados_edicao["tipo"]] if dados_edicao else rotulos_tipo[0]
    tipo_label = st.selectbox(
        "Tipo", rotulos_tipo, index=rotulos_tipo.index(tipo_default), key=f"tipo_{sufixo}"
    )
    tipo = TIPOS_INTERNO[tipo_label]

candidatos_pai = [
    c
    for c in todas_categorias
    if c["ativa"] and c["id"] != editando_id and (c["tipo"] == "ambos" or c["tipo"] == tipo)
]
opcoes_pai = [None] + [c["id"] for c in candidatos_pai]
pai_default = dados_edicao["categoria_pai_id"] if dados_edicao else None
if pai_default not in opcoes_pai:
    pai_default = None
categoria_pai_id = st.selectbox(
    "Categoria pai",
    opcoes_pai,
    index=opcoes_pai.index(pai_default),
    format_func=lambda cid: (
        "Nenhuma (categoria principal)" if cid is None else caminho_categoria(cid)
    ),
    key=f"pai_{sufixo}",
)

ativa = st.checkbox(
    "Ativa", value=dados_edicao["ativa"] if dados_edicao else True, key=f"ativa_{sufixo}"
)

col_salvar, col_cancelar = st.columns([1, 1])
with col_salvar:
    rotulo_botao = "Salvar edição" if editando_id else "Criar categoria"
    if st.button(rotulo_botao, type="primary", key=f"salvar_{sufixo}"):
        try:
            if editando_id:
                categorias.atualizar_categoria(
                    editando_id,
                    nome=nome,
                    tipo=tipo,
                    categoria_pai_id=categoria_pai_id,
                    ativa=ativa,
                )
                _definir_mensagem("Categoria atualizada com sucesso.")
            else:
                categorias.criar_categoria(
                    nome=nome, tipo=tipo, categoria_pai_id=categoria_pai_id
                )
                _definir_mensagem("Categoria criada com sucesso.")
            st.session_state["cat_editando_id"] = None
            st.session_state["cat_form_versao"] += 1
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Ocorreu um erro inesperado ao salvar a categoria.")

if editando_id:
    with col_cancelar:
        if st.button("Cancelar edição", key=f"cancelar_{sufixo}"):
            st.session_state["cat_editando_id"] = None
            st.session_state["cat_form_versao"] += 1
            st.rerun()


# ---------------------------------------------------------------------
# Diálogo de confirmação de exclusão
# ---------------------------------------------------------------------
@st.dialog("Confirmar exclusão")
def _confirmar_exclusao(categoria_id: int) -> None:
    categoria = categorias.obter_categoria(categoria_id)
    if categoria is None:
        st.warning("Esta categoria já não existe mais.")
        if st.button("Fechar", key="cat_confirmar_exclusao_fechar"):
            st.session_state["cat_excluir_id"] = None
            st.rerun()
        return

    st.write(f"Tem certeza que deseja excluir a categoria **{caminho_categoria(categoria_id)}**?")
    st.caption(
        "Se a categoria tiver lançamentos, regras ou subcategorias vinculadas, "
        "ela será desativada em vez de excluída."
    )
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="cat_confirmar_exclusao_sim"):
            try:
                categorias.excluir_categoria(categoria_id)
                ainda_existe = categorias.obter_categoria(categoria_id)
                if ainda_existe is None:
                    _definir_mensagem("Categoria excluída com sucesso.")
                else:
                    _definir_mensagem(
                        "Categoria possui dependências vinculadas e foi desativada."
                    )
                st.session_state["cat_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="cat_confirmar_exclusao_cancelar"):
            st.session_state["cat_excluir_id"] = None
            st.rerun()


if st.session_state["cat_excluir_id"] is not None:
    _confirmar_exclusao(st.session_state["cat_excluir_id"])


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------
st.divider()
st.subheader("Categorias cadastradas")

mostrar_inativas = st.checkbox(
    "Mostrar categorias inativas", value=True, key="cat_mostrar_inativas"
)
lista_categorias = [c for c in todas_categorias if mostrar_inativas or c["ativa"]]

if not lista_categorias:
    st.info(
        "Nenhuma categoria cadastrada ainda. Use o formulário acima para criar a primeira."
    )
else:
    larguras = [3, 1, 1, 1, 1]
    titulos = ["Categoria", "Tipo", "Ativa", "", ""]
    for coluna, titulo in zip(st.columns(larguras), titulos):
        if titulo:
            coluna.markdown(f"**{titulo}**")

    for categoria in sorted(lista_categorias, key=lambda c: caminho_categoria(c["id"])):
        colunas = st.columns(larguras)
        colunas[0].write(caminho_categoria(categoria["id"]))
        colunas[1].write(TIPOS_LABEL.get(categoria["tipo"], categoria["tipo"]))
        colunas[2].write("✅ Ativa" if categoria["ativa"] else "⛔ Inativa")
        if colunas[3].button("Editar", key=f"cat_editar_{categoria['id']}"):
            st.session_state["cat_editando_id"] = categoria["id"]
            st.session_state["cat_form_versao"] += 1
            st.rerun()
        if colunas[4].button("Excluir", key=f"cat_excluir_{categoria['id']}"):
            st.session_state["cat_excluir_id"] = categoria["id"]
            st.rerun()
