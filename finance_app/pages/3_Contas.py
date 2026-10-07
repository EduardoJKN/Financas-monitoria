from datetime import date
from decimal import Decimal

import streamlit as st

from src import contas, resumo_financeiro as resumo
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import formatar_moeda, texto_para_decimal

st.title("Contas")

TIPOS_LABEL = {
    "conta_corrente": "Conta corrente",
    "conta_digital": "Conta digital",
    "poupanca": "Poupança",
    "dinheiro": "Dinheiro",
    "investimento": "Investimento",
    "outro": "Outro",
}
TIPOS_INTERNO = {rotulo: interno for interno, rotulo in TIPOS_LABEL.items()}

# ---------------------------------------------------------------------
# Estado da página
# ---------------------------------------------------------------------
st.session_state.setdefault("conta_editando_id", None)
st.session_state.setdefault("conta_form_versao", 0)
st.session_state.setdefault("conta_excluir_id", None)

mensagem = st.session_state.pop("conta_mensagem", None)
if mensagem:
    st.success(mensagem)


def _definir_mensagem(texto: str) -> None:
    st.session_state["conta_mensagem"] = texto


# ---------------------------------------------------------------------
# Formulário de criação/edição
# ---------------------------------------------------------------------
editando_id = st.session_state["conta_editando_id"]
dados_edicao = contas.obter_conta(editando_id) if editando_id is not None else None
if editando_id is not None and dados_edicao is None:
    st.session_state["conta_editando_id"] = None
    editando_id = None

sufixo = (
    f"edit_{editando_id}_{st.session_state['conta_form_versao']}"
    if editando_id
    else f"novo_{st.session_state['conta_form_versao']}"
)

st.subheader(f"Editar conta #{editando_id}" if editando_id else "Nova conta")

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

col_c, col_d = st.columns(2)
with col_c:
    instituicao = st.text_input(
        "Instituição",
        value=(dados_edicao.get("instituicao") or "") if dados_edicao else "",
        key=f"instituicao_{sufixo}",
    )
with col_d:
    saldo_inicial_texto = st.text_input(
        "Saldo inicial (R$)",
        value=str(dados_edicao["saldo_inicial"]) if dados_edicao else "0",
        placeholder="Ex.: 1234,56",
        key=f"saldo_inicial_{sufixo}",
    )

tem_data_saldo_inicial = st.checkbox(
    "Esse saldo inicial tem uma data de referência (recomendado)?",
    value=bool(dados_edicao and dados_edicao.get("data_saldo_inicial")),
    key=f"tem_data_saldo_inicial_{sufixo}",
    help=(
        "A data em que o saldo acima era o saldo real da conta no banco. "
        "Movimentações até essa data não são somadas de novo no cálculo do "
        "saldo atual, evitando dupla contagem."
    ),
)
data_saldo_inicial = None
if tem_data_saldo_inicial:
    data_saldo_inicial = st.date_input(
        "Saldo inicial válido em",
        value=(dados_edicao.get("data_saldo_inicial") or date.today()) if dados_edicao else date.today(),
        key=f"data_saldo_inicial_{sufixo}",
    )

ativa = st.checkbox(
    "Ativa", value=dados_edicao["ativa"] if dados_edicao else True, key=f"ativa_{sufixo}"
)

col_salvar, col_cancelar = st.columns([1, 1])
with col_salvar:
    rotulo_botao = "Salvar edição" if editando_id else "Criar conta"
    if st.button(rotulo_botao, type="primary", key=f"salvar_{sufixo}"):
        try:
            saldo_inicial_decimal = texto_para_decimal(saldo_inicial_texto)
            if editando_id:
                contas.atualizar_conta(
                    editando_id,
                    nome=nome,
                    tipo=tipo,
                    instituicao=instituicao or None,
                    saldo_inicial=saldo_inicial_decimal,
                    data_saldo_inicial=data_saldo_inicial,
                    ativa=ativa,
                )
                _definir_mensagem("Conta atualizada com sucesso.")
            else:
                contas.criar_conta(
                    nome=nome,
                    tipo=tipo,
                    instituicao=instituicao or None,
                    saldo_inicial=saldo_inicial_decimal,
                    data_saldo_inicial=data_saldo_inicial,
                )
                _definir_mensagem("Conta criada com sucesso.")
            st.session_state["conta_editando_id"] = None
            st.session_state["conta_form_versao"] += 1
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Ocorreu um erro inesperado ao salvar a conta.")

if editando_id:
    with col_cancelar:
        if st.button("Cancelar edição", key=f"cancelar_{sufixo}"):
            st.session_state["conta_editando_id"] = None
            st.session_state["conta_form_versao"] += 1
            st.rerun()


# ---------------------------------------------------------------------
# Diálogo de confirmação de exclusão
# ---------------------------------------------------------------------
@st.dialog("Confirmar exclusão")
def _confirmar_exclusao(conta_id: int) -> None:
    conta = contas.obter_conta(conta_id)
    if conta is None:
        st.warning("Esta conta já não existe mais.")
        if st.button("Fechar", key="conta_confirmar_exclusao_fechar"):
            st.session_state["conta_excluir_id"] = None
            st.rerun()
        return

    st.write(f"Tem certeza que deseja excluir a conta **{conta['nome']}**?")
    st.caption(
        "Se a conta tiver lançamentos vinculados, ela será desativada em vez de excluída."
    )
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="conta_confirmar_exclusao_sim"):
            try:
                contas.excluir_conta(conta_id)
                ainda_existe = contas.obter_conta(conta_id)
                if ainda_existe is None:
                    _definir_mensagem("Conta excluída com sucesso.")
                else:
                    _definir_mensagem(
                        "Conta possui lançamentos vinculados e foi desativada."
                    )
                st.session_state["conta_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="conta_confirmar_exclusao_cancelar"):
            st.session_state["conta_excluir_id"] = None
            st.rerun()


if st.session_state["conta_excluir_id"] is not None:
    _confirmar_exclusao(st.session_state["conta_excluir_id"])


# ---------------------------------------------------------------------
# Conciliação de saldo (Parte 10)
# ---------------------------------------------------------------------
st.session_state.setdefault("conta_conciliar_id", None)


@st.dialog("Conciliar conta")
def _conciliar_conta(conta_id: int) -> None:
    conta = contas.obter_conta(conta_id)
    if conta is None:
        st.warning("Esta conta já não existe mais.")
        if st.button("Fechar", key="conciliar_fechar"):
            st.session_state["conta_conciliar_id"] = None
            st.rerun()
        return

    st.write(f"**Conta:** {conta['nome']}")
    data_referencia = st.date_input(
        "Data em que o saldo abaixo é válido", value=date.today(), key="conciliar_data"
    )
    saldo_banco_texto = st.text_input(
        "Saldo informado pelo banco/extrato nessa data (R$)",
        key="conciliar_saldo_banco",
        placeholder="Ex.: 1234,56",
    )

    if saldo_banco_texto.strip():
        try:
            saldo_banco_decimal = texto_para_decimal(saldo_banco_texto)
            previa = resumo.pre_visualizar_conciliacao(conta_id, data_referencia, saldo_banco_decimal)
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
            previa = None

        if previa is not None:
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.metric("Saldo calculado hoje", formatar_moeda(previa["saldo_calculado_atual"]))
            col_p2.metric("Saldo informado", formatar_moeda(previa["saldo_informado"]))
            col_p3.metric("Diferença", formatar_moeda(previa["diferenca"]))
            st.caption(
                f"Depois de conciliar: saldo_inicial passa a ser "
                f"{formatar_moeda(saldo_banco_decimal)} com data de referência "
                f"{data_referencia.strftime('%d/%m/%Y')}. Lançamentos até essa data "
                "continuam no histórico, só não são somados de novo no cálculo do saldo."
            )
            if st.button("Confirmar conciliação", type="primary", key="conciliar_confirmar"):
                try:
                    resultado = resumo.conciliar_conta(conta_id, data_referencia, saldo_banco_decimal)
                    st.session_state["conta_conciliar_id"] = None
                    _definir_mensagem(
                        f"Conta conciliada. Novo saldo: {formatar_moeda(resultado['saldo_atual'])}."
                    )
                    st.rerun()
                except (ValueError, ErroBancoDeDados) as exc:
                    st.error(str(exc))

    if st.button("Cancelar", key="conciliar_cancelar"):
        st.session_state["conta_conciliar_id"] = None
        st.rerun()


if st.session_state["conta_conciliar_id"] is not None:
    _conciliar_conta(st.session_state["conta_conciliar_id"])


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------
st.divider()
st.subheader("Contas cadastradas")

mostrar_inativas = st.checkbox(
    "Mostrar contas inativas", value=True, key="conta_mostrar_inativas"
)

try:
    lista_contas = contas.listar_contas(incluir_inativas=mostrar_inativas)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    lista_contas = []

if not lista_contas:
    st.info("Nenhuma conta cadastrada ainda. Use o formulário acima para criar a primeira.")
else:
    larguras = [2, 2, 2, 2, 2, 1, 1, 1, 1]
    titulos = ["Nome", "Tipo", "Instituição", "Saldo atual", "Conciliação", "", "", "", ""]
    for coluna, titulo in zip(st.columns(larguras), titulos):
        if titulo:
            coluna.markdown(f"**{titulo}**")

    for conta in lista_contas:
        colunas = st.columns(larguras)
        colunas[0].write(conta["nome"] if conta["ativa"] else f"{conta['nome']} (inativa)")
        colunas[1].write(TIPOS_LABEL.get(conta["tipo"], conta["tipo"]))
        colunas[2].write(conta["instituicao"] or "—")
        try:
            saldo_atual = resumo.calcular_saldo_conta(conta["id"])
            colunas[3].write(formatar_moeda(saldo_atual))
        except ErroBancoDeDados:
            colunas[3].write("—")
        if conta.get("data_saldo_inicial"):
            colunas[4].write(f"✅ {conta['data_saldo_inicial'].strftime('%d/%m/%Y')}")
        else:
            colunas[4].write("⚠️ Sem referência")
        if colunas[5].button("Editar", key=f"conta_editar_{conta['id']}"):
            st.session_state["conta_editando_id"] = conta["id"]
            st.session_state["conta_form_versao"] += 1
            st.rerun()
        if colunas[6].button("Conciliar", key=f"conta_conciliar_{conta['id']}"):
            st.session_state["conta_conciliar_id"] = conta["id"]
            st.rerun()
        rotulo_toggle = "Desativar" if conta["ativa"] else "Ativar"
        if colunas[7].button(rotulo_toggle, key=f"conta_toggle_{conta['id']}"):
            try:
                contas.atualizar_conta(conta["id"], ativa=not conta["ativa"])
                _definir_mensagem(
                    "Conta desativada com sucesso."
                    if conta["ativa"]
                    else "Conta ativada com sucesso."
                )
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
        if colunas[8].button("Excluir", key=f"conta_excluir_{conta['id']}"):
            st.session_state["conta_excluir_id"] = conta["id"]
            st.rerun()
