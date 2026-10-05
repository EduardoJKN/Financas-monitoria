from datetime import date

import streamlit as st

from src import metas
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import formatar_moeda, texto_para_decimal

st.set_page_config(page_title="Metas | Economia UaU", layout="wide")
st.title("Metas")

# ---------------------------------------------------------------------
# Estado da página
# ---------------------------------------------------------------------
st.session_state.setdefault("meta_editando_id", None)
st.session_state.setdefault("meta_form_versao", 0)
st.session_state.setdefault("meta_excluir_id", None)

mensagem = st.session_state.pop("meta_mensagem", None)
if mensagem:
    st.success(mensagem)


def _definir_mensagem(texto: str) -> None:
    st.session_state["meta_mensagem"] = texto


# ---------------------------------------------------------------------
# Formulário de criação/edição
# ---------------------------------------------------------------------
editando_id = st.session_state["meta_editando_id"]
dados_edicao = metas.obter_meta(editando_id) if editando_id is not None else None
if editando_id is not None and dados_edicao is None:
    st.session_state["meta_editando_id"] = None
    editando_id = None

sufixo = (
    f"edit_{editando_id}_{st.session_state['meta_form_versao']}"
    if editando_id
    else f"novo_{st.session_state['meta_form_versao']}"
)

st.subheader(f"Editar meta #{editando_id}" if editando_id else "Nova meta")

col_a, col_b = st.columns(2)
with col_a:
    nome = st.text_input(
        "Nome", value=dados_edicao["nome"] if dados_edicao else "", key=f"meta_nome_{sufixo}"
    )
with col_b:
    descricao = st.text_input(
        "Descrição",
        value=(dados_edicao.get("descricao") or "") if dados_edicao else "",
        key=f"meta_descricao_{sufixo}",
    )

col_c, col_d = st.columns(2)
with col_c:
    valor_alvo_texto = st.text_input(
        "Valor alvo (R$)",
        value=str(dados_edicao["valor_alvo"]) if dados_edicao else "",
        placeholder="Ex.: 30000,00",
        key=f"meta_valor_alvo_{sufixo}",
    )
with col_d:
    valor_atual_texto = st.text_input(
        "Valor atual (R$)",
        value=str(dados_edicao["valor_atual"]) if dados_edicao else "0",
        placeholder="Ex.: 10000,00",
        key=f"meta_valor_atual_{sufixo}",
    )

col_e, col_f = st.columns(2)
with col_e:
    data_inicio = st.date_input(
        "Data de início",
        value=dados_edicao["data_inicio"] if dados_edicao else date.today(),
        key=f"meta_data_inicio_{sufixo}",
    )
with col_f:
    tem_data_limite_default = bool(dados_edicao and dados_edicao.get("data_limite"))
    tem_data_limite = st.checkbox(
        "Definir data limite", value=tem_data_limite_default, key=f"meta_tem_limite_{sufixo}"
    )
    data_limite = None
    if tem_data_limite:
        data_limite = st.date_input(
            "Data limite",
            value=(
                dados_edicao["data_limite"]
                if dados_edicao and dados_edicao.get("data_limite")
                else date.today()
            ),
            key=f"meta_data_limite_{sufixo}",
        )

col_salvar, col_cancelar = st.columns([1, 1])
with col_salvar:
    rotulo_botao = "Salvar edição" if editando_id else "Criar meta"
    if st.button(rotulo_botao, type="primary", key=f"meta_salvar_{sufixo}"):
        try:
            valor_alvo_decimal = texto_para_decimal(valor_alvo_texto)
            valor_atual_decimal = texto_para_decimal(valor_atual_texto)
            if editando_id:
                metas.atualizar_meta(
                    editando_id,
                    nome=nome,
                    descricao=descricao or None,
                    valor_alvo=valor_alvo_decimal,
                    valor_atual=valor_atual_decimal,
                    data_inicio=data_inicio,
                    data_limite=data_limite,
                )
                _definir_mensagem("Meta atualizada com sucesso.")
            else:
                metas.criar_meta(
                    nome=nome,
                    data_inicio=data_inicio,
                    valor_alvo=valor_alvo_decimal,
                    valor_atual=valor_atual_decimal,
                    descricao=descricao or None,
                    data_limite=data_limite,
                )
                _definir_mensagem("Meta criada com sucesso.")
            st.session_state["meta_editando_id"] = None
            st.session_state["meta_form_versao"] += 1
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Ocorreu um erro inesperado ao salvar a meta.")

if editando_id:
    with col_cancelar:
        if st.button("Cancelar edição", key=f"meta_cancelar_{sufixo}"):
            st.session_state["meta_editando_id"] = None
            st.session_state["meta_form_versao"] += 1
            st.rerun()


# ---------------------------------------------------------------------
# Diálogo de confirmação de exclusão
# ---------------------------------------------------------------------
@st.dialog("Confirmar exclusão")
def _confirmar_exclusao(meta_id: int) -> None:
    meta = metas.obter_meta(meta_id)
    if meta is None:
        st.warning("Esta meta já não existe mais.")
        if st.button("Fechar", key="meta_confirmar_exclusao_fechar"):
            st.session_state["meta_excluir_id"] = None
            st.rerun()
        return

    st.write(f"Tem certeza que deseja excluir a meta **{meta['nome']}**?")
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="meta_confirmar_exclusao_sim"):
            try:
                metas.excluir_meta(meta_id)
                _definir_mensagem("Meta excluída com sucesso.")
                st.session_state["meta_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="meta_confirmar_exclusao_cancelar"):
            st.session_state["meta_excluir_id"] = None
            st.rerun()


if st.session_state["meta_excluir_id"] is not None:
    _confirmar_exclusao(st.session_state["meta_excluir_id"])


# ---------------------------------------------------------------------
# Diálogo de atualização rápida do valor atual
# ---------------------------------------------------------------------
@st.dialog("Atualizar valor atual")
def _atualizar_valor_atual(meta_id: int) -> None:
    meta = metas.obter_meta(meta_id)
    if meta is None:
        st.warning("Esta meta já não existe mais.")
        if st.button("Fechar", key="meta_valor_fechar"):
            st.session_state["meta_atualizar_valor_id"] = None
            st.rerun()
        return

    st.write(f"Meta: **{meta['nome']}**")
    novo_valor_texto = st.text_input(
        "Novo valor atual (R$)", value=str(meta["valor_atual"]), key="meta_novo_valor_texto"
    )
    if st.button("Salvar valor atual", type="primary", key="meta_novo_valor_salvar"):
        try:
            novo_valor = texto_para_decimal(novo_valor_texto)
            metas.atualizar_meta(meta_id, valor_atual=novo_valor)
            _definir_mensagem("Valor atual atualizado com sucesso.")
            st.session_state["meta_atualizar_valor_id"] = None
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
    if st.button("Cancelar", key="meta_novo_valor_cancelar"):
        st.session_state["meta_atualizar_valor_id"] = None
        st.rerun()


st.session_state.setdefault("meta_atualizar_valor_id", None)
if st.session_state["meta_atualizar_valor_id"] is not None:
    _atualizar_valor_atual(st.session_state["meta_atualizar_valor_id"])


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------
st.divider()
st.subheader("Suas metas")

try:
    lista_metas = metas.listar_metas()
except ErroBancoDeDados as exc:
    st.error(str(exc))
    lista_metas = []

if not lista_metas:
    st.info("Nenhuma meta cadastrada ainda. Use o formulário acima para criar a primeira.")
else:
    hoje = date.today()
    for meta in lista_metas:
        progresso = metas.calcular_progresso_meta(meta["id"])

        with st.container(border=True):
            st.markdown(f"### {meta['nome']}")
            if meta.get("descricao"):
                st.caption(meta["descricao"])

            st.write(
                f"{formatar_moeda(progresso['valor_atual'])} de "
                f"{formatar_moeda(progresso['valor_alvo'])}"
            )
            percentual_float = float(progresso["percentual"]) / 100
            st.progress(percentual_float)
            st.write(f"{progresso['percentual']:.0f}% concluído")

            if progresso["concluida"]:
                st.success("🎉 Meta concluída!")
            else:
                st.write(f"Faltam {formatar_moeda(progresso['valor_restante'])}")

            if meta.get("data_limite"):
                atrasada = (not progresso["concluida"]) and meta["data_limite"] < hoje
                texto_prazo = f"Prazo: {meta['data_limite'].strftime('%d/%m/%Y')}"
                if atrasada:
                    st.warning(f"{texto_prazo} — prazo vencido")
                else:
                    st.caption(texto_prazo)

            status = (
                "Concluída"
                if progresso["concluida"]
                else (
                    "Atrasada"
                    if meta.get("data_limite") and meta["data_limite"] < hoje
                    else "Em andamento"
                )
            )
            st.caption(f"Status: {status}")

            col_1, col_2, col_3 = st.columns(3)
            if col_1.button("Editar", key=f"meta_editar_{meta['id']}"):
                st.session_state["meta_editando_id"] = meta["id"]
                st.session_state["meta_form_versao"] += 1
                st.rerun()
            if col_2.button("Atualizar valor atual", key=f"meta_valor_{meta['id']}"):
                st.session_state["meta_atualizar_valor_id"] = meta["id"]
                st.rerun()
            if col_3.button("Excluir", key=f"meta_excluir_{meta['id']}"):
                st.session_state["meta_excluir_id"] = meta["id"]
                st.rerun()
