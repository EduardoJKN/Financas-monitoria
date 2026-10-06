import streamlit as st

from src import categorias, categorizador
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import badge_tipo_transacao, formatar_moeda

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


# =======================================================================
# Regras de categorização
# =======================================================================
st.divider()
st.header("Regras de categorização")
st.caption(
    "Regras aplicadas automaticamente durante a importação de extratos, "
    "em ordem de prioridade (maior prioridade primeiro)."
)

OPERADORES_LABEL = {"contem": "Contém", "comeca_com": "Começa com", "igual": "Igual"}
OPERADORES_INTERNO = {rotulo: interno for interno, rotulo in OPERADORES_LABEL.items()}

st.session_state.setdefault("regra_editando_id", None)
st.session_state.setdefault("regra_form_versao", 0)
st.session_state.setdefault("regra_excluir_id", None)

mensagem_regra = st.session_state.pop("regra_mensagem", None)
if mensagem_regra:
    st.success(mensagem_regra)


def _definir_mensagem_regra(texto: str) -> None:
    st.session_state["regra_mensagem"] = texto


try:
    todas_regras = categorizador.listar_regras(incluir_inativas=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    todas_regras = []

categorias_ativas = [c for c in todas_categorias if c["ativa"]]
categorias_ativas_ordenadas = sorted(categorias_ativas, key=lambda c: caminho_categoria(c["id"]))

if not categorias_ativas_ordenadas:
    st.info("Cadastre ao menos uma categoria ativa acima para poder criar regras.")
else:
    regra_editando_id = st.session_state["regra_editando_id"]
    regra_edicao = next(
        (r for r in todas_regras if r["id"] == regra_editando_id), None
    )
    if regra_editando_id is not None and regra_edicao is None:
        st.session_state["regra_editando_id"] = None
        regra_editando_id = None

    sufixo_regra = (
        f"edit_{regra_editando_id}_{st.session_state['regra_form_versao']}"
        if regra_editando_id
        else f"novo_{st.session_state['regra_form_versao']}"
    )

    st.subheader(
        f"Editar regra #{regra_editando_id}" if regra_editando_id else "Nova regra"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        texto_busca = st.text_input(
            "Texto procurado",
            value=regra_edicao["texto_busca"] if regra_edicao else "",
            placeholder="Ex.: IFOOD",
            key=f"regra_texto_{sufixo_regra}",
        )
    with col_b:
        rotulos_operador = list(OPERADORES_LABEL.values())
        operador_default = (
            OPERADORES_LABEL[regra_edicao["operador"]] if regra_edicao else rotulos_operador[0]
        )
        operador_label = st.selectbox(
            "Operador",
            rotulos_operador,
            index=rotulos_operador.index(operador_default),
            key=f"regra_operador_{sufixo_regra}",
        )
        operador = OPERADORES_INTERNO[operador_label]

    col_c, col_d = st.columns(2)
    with col_c:
        ids_categoria_regra = [c["id"] for c in categorias_ativas_ordenadas]
        categoria_default = (
            regra_edicao["categoria_id"] if regra_edicao else ids_categoria_regra[0]
        )
        if categoria_default not in ids_categoria_regra:
            categoria_default = ids_categoria_regra[0]
        categoria_id_regra = st.selectbox(
            "Categoria",
            ids_categoria_regra,
            index=ids_categoria_regra.index(categoria_default),
            format_func=caminho_categoria,
            key=f"regra_categoria_{sufixo_regra}",
        )
    with col_d:
        prioridade = st.number_input(
            "Prioridade",
            value=int(regra_edicao["prioridade"]) if regra_edicao else 0,
            step=1,
            format="%d",
            key=f"regra_prioridade_{sufixo_regra}",
        )

    ativa_regra = st.checkbox(
        "Ativa",
        value=regra_edicao["ativa"] if regra_edicao else True,
        key=f"regra_ativa_{sufixo_regra}",
    )

    col_salvar_regra, col_cancelar_regra = st.columns([1, 1])
    with col_salvar_regra:
        rotulo_botao_regra = "Salvar edição" if regra_editando_id else "Criar regra"
        if st.button(rotulo_botao_regra, type="primary", key=f"regra_salvar_{sufixo_regra}"):
            try:
                if regra_editando_id:
                    categorizador.atualizar_regra(
                        regra_editando_id,
                        texto_busca=texto_busca,
                        operador=operador,
                        categoria_id=categoria_id_regra,
                        prioridade=int(prioridade),
                        ativa=ativa_regra,
                    )
                    _definir_mensagem_regra("Regra atualizada com sucesso.")
                    regra_id_salva = regra_editando_id
                else:
                    regra_id_salva = categorizador.criar_regra(
                        texto_busca=texto_busca,
                        operador=operador,
                        categoria_id=categoria_id_regra,
                        prioridade=int(prioridade),
                    )
                    _definir_mensagem_regra("Regra criada com sucesso.")
                st.session_state["regra_editando_id"] = None
                st.session_state["regra_form_versao"] += 1
                # dispara a sugestão de revisão retroativa (secção abaixo)
                st.session_state["regra_revisar_id"] = regra_id_salva
                st.session_state["regra_revisar_abrir_preview"] = False
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Ocorreu um erro inesperado ao salvar a regra.")

    if regra_editando_id:
        with col_cancelar_regra:
            if st.button("Cancelar edição", key=f"regra_cancelar_{sufixo_regra}"):
                st.session_state["regra_editando_id"] = None
                st.session_state["regra_form_versao"] += 1
                st.rerun()


@st.dialog("Confirmar exclusão")
def _confirmar_exclusao_regra(regra_id: int) -> None:
    regra = categorizador.obter_regra(regra_id)
    if regra is None:
        st.warning("Esta regra já não existe mais.")
        if st.button("Fechar", key="regra_confirmar_exclusao_fechar"):
            st.session_state["regra_excluir_id"] = None
            st.rerun()
        return

    st.write(
        f"Tem certeza que deseja excluir a regra **{regra['texto_busca']}** "
        f"({OPERADORES_LABEL.get(regra['operador'], regra['operador'])})?"
    )
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="regra_confirmar_exclusao_sim"):
            try:
                categorizador.excluir_regra(regra_id)
                _definir_mensagem_regra("Regra excluída com sucesso.")
                st.session_state["regra_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="regra_confirmar_exclusao_cancelar"):
            st.session_state["regra_excluir_id"] = None
            st.rerun()


if st.session_state["regra_excluir_id"] is not None:
    _confirmar_exclusao_regra(st.session_state["regra_excluir_id"])


st.subheader("Regras cadastradas")

mostrar_regras_inativas = st.checkbox(
    "Mostrar regras inativas", value=True, key="regra_mostrar_inativas"
)
lista_regras = [r for r in todas_regras if mostrar_regras_inativas or r["ativa"]]

if not lista_regras:
    st.info("Nenhuma regra cadastrada ainda. Use o formulário acima para criar a primeira.")
else:
    larguras_regra = [2, 1, 3, 1, 1, 1, 1, 1]
    titulos_regra = [
        "Texto procurado", "Operador", "Categoria", "Prioridade", "Ativa", "", "", ""
    ]
    for coluna, titulo in zip(st.columns(larguras_regra), titulos_regra):
        if titulo:
            coluna.markdown(f"**{titulo}**")

    for regra in sorted(lista_regras, key=lambda r: (-r["prioridade"], r["id"])):
        colunas = st.columns(larguras_regra)
        colunas[0].write(regra["texto_busca"])
        colunas[1].write(OPERADORES_LABEL.get(regra["operador"], regra["operador"]))
        colunas[2].write(caminho_categoria(regra["categoria_id"]))
        colunas[3].write(str(regra["prioridade"]))
        colunas[4].write("✅ Ativa" if regra["ativa"] else "⛔ Inativa")
        if colunas[5].button("Editar", key=f"regra_editar_{regra['id']}"):
            st.session_state["regra_editando_id"] = regra["id"]
            st.session_state["regra_form_versao"] += 1
            st.rerun()
        rotulo_toggle_regra = "Desativar" if regra["ativa"] else "Ativar"
        if colunas[6].button(rotulo_toggle_regra, key=f"regra_toggle_{regra['id']}"):
            try:
                categorizador.atualizar_regra(regra["id"], ativa=not regra["ativa"])
                _definir_mensagem_regra(
                    "Regra desativada com sucesso."
                    if regra["ativa"]
                    else "Regra ativada com sucesso."
                )
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
        if colunas[7].button("Excluir", key=f"regra_excluir_{regra['id']}"):
            st.session_state["regra_excluir_id"] = regra["id"]
            st.rerun()


# =======================================================================
# Revisão retroativa: aplicar a regra recém criada/editada a lançamentos
# já existentes no banco (nunca sobrescreve categorias sem ação explícita)
# =======================================================================
st.session_state.setdefault("regra_revisar_id", None)
st.session_state.setdefault("regra_revisar_abrir_preview", False)

regra_revisar_id = st.session_state["regra_revisar_id"]
if regra_revisar_id is not None:
    try:
        compativeis_sem_categoria = categorizador.buscar_transacoes_compativeis_regra(
            regra_revisar_id, somente_sem_categoria=True
        )
    except (ValueError, ErroBancoDeDados):
        compativeis_sem_categoria = []
        st.session_state["regra_revisar_id"] = None
        regra_revisar_id = None

if regra_revisar_id is not None and not compativeis_sem_categoria:
    # nada para revisar (nenhum lançamento sem categoria corresponde)
    st.session_state["regra_revisar_id"] = None
    regra_revisar_id = None

if regra_revisar_id is not None:
    st.divider()
    st.info(
        f"Esta regra encontrou {len(compativeis_sem_categoria)} lançamento(s) "
        "existente(s) sem categoria."
    )

    if not st.session_state["regra_revisar_abrir_preview"]:
        if st.button(
            "Revisar e aplicar aos lançamentos existentes", key="regra_revisar_abrir"
        ):
            st.session_state["regra_revisar_abrir_preview"] = True
            st.rerun()
    else:
        incluir_categorizados = st.checkbox(
            "Incluir lançamentos que já possuem categoria",
            value=False,
            key="regra_revisar_incluir_categorizados",
        )

        try:
            compativeis_preview = categorizador.buscar_transacoes_compativeis_regra(
                regra_revisar_id, somente_sem_categoria=not incluir_categorizados
            )
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
            compativeis_preview = []

        regra_alvo = categorizador.obter_regra(regra_revisar_id)
        categoria_sugerida_nome = (
            caminho_categoria(regra_alvo["categoria_id"]) if regra_alvo else "—"
        )

        if incluir_categorizados:
            st.warning(
                "Lançamentos já categorizados aparecem abaixo. Se selecionados e "
                "aplicados, a categoria atual será substituída."
            )

        if not compativeis_preview:
            st.info("Nenhum lançamento compatível encontrado com os filtros atuais.")
        else:
            larguras_preview = [1, 1, 3, 1, 1, 2, 2]
            titulos_preview = [
                "Aplicar", "Data", "Descrição", "Tipo", "Valor",
                "Categoria atual", "Categoria sugerida",
            ]
            for coluna, titulo in zip(st.columns(larguras_preview), titulos_preview):
                coluna.markdown(f"**{titulo}**")

            selecionados_ids = []
            for transacao in compativeis_preview:
                colunas_p = st.columns(larguras_preview)
                chave_check = f"regra_revisar_sel_{regra_revisar_id}_{transacao['id']}"
                selecionado = colunas_p[0].checkbox(
                    "",
                    value=(transacao["categoria_id"] is None),
                    key=chave_check,
                    label_visibility="collapsed",
                )
                colunas_p[1].write(transacao["data_transacao"].strftime("%d/%m/%Y"))
                colunas_p[2].write(transacao["descricao"])
                colunas_p[3].write(badge_tipo_transacao(transacao["tipo"]))
                colunas_p[4].write(formatar_moeda(transacao["valor"]))
                colunas_p[5].write(caminho_categoria(transacao["categoria_id"]))
                colunas_p[6].write(categoria_sugerida_nome)
                if selecionado:
                    selecionados_ids.append(transacao["id"])

            col_aplicar, col_fechar = st.columns([1, 1])
            with col_aplicar:
                if st.button(
                    "Aplicar categoria aos lançamentos selecionados",
                    type="primary",
                    key="regra_revisar_aplicar",
                ):
                    try:
                        total_aplicado = categorizador.aplicar_regra_em_transacoes_existentes(
                            regra_revisar_id,
                            transacao_ids=selecionados_ids,
                            somente_sem_categoria=not incluir_categorizados,
                        )
                        _definir_mensagem_regra(
                            f"{total_aplicado} lançamento(s) categorizado(s) com sucesso."
                        )
                        st.session_state["regra_revisar_id"] = None
                        st.session_state["regra_revisar_abrir_preview"] = False
                        st.rerun()
                    except (ValueError, ErroBancoDeDados) as exc:
                        st.error(str(exc))
            with col_fechar:
                if st.button("Fechar", key="regra_revisar_fechar"):
                    st.session_state["regra_revisar_id"] = None
                    st.session_state["regra_revisar_abrir_preview"] = False
                    st.rerun()


# =======================================================================
# Reaplicar todas as regras aos lançamentos sem categoria
# =======================================================================
st.divider()
st.subheader("Reaplicar regras em lote")
st.caption(
    "Usa as regras ativas (por prioridade) para categorizar lançamentos antigos "
    "que ainda não têm categoria. Nunca sobrescreve categorias já existentes."
)

st.session_state.setdefault("regra_previa_todas", None)

if st.button("Verificar lançamentos sem categoria", key="regra_verificar_todas"):
    try:
        st.session_state["regra_previa_todas"] = categorizador.prever_aplicacao_todas_regras()
    except ErroBancoDeDados as exc:
        st.error(str(exc))
        st.session_state["regra_previa_todas"] = None

previa_todas = st.session_state["regra_previa_todas"]
if previa_todas is not None:
    if not previa_todas:
        st.info("Nenhum lançamento sem categoria corresponde às regras ativas no momento.")
    else:
        st.write(f"**{len(previa_todas)} lançamento(s) serão categorizados.**")
        if st.button(
            "Aplicar todas as regras aos lançamentos sem categoria",
            type="primary",
            key="regra_aplicar_todas_confirmar",
        ):
            try:
                ids_para_aplicar = [item["id"] for item in previa_todas]
                total = categorizador.aplicar_todas_regras_em_transacoes_sem_categoria(
                    ids_para_aplicar
                )
                st.session_state["regra_previa_todas"] = None
                _definir_mensagem_regra(f"{total} lançamentos categorizados com sucesso.")
                st.rerun()
            except ErroBancoDeDados as exc:
                st.error(str(exc))
