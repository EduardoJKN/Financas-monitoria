from datetime import date

import streamlit as st

from src import cartoes, contas, faturas
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import (
    badge_pagamento_fatura,
    container_linha_colorida,
    formatar_moeda,
    texto_para_decimal,
)

st.title("Cartões")

STATUS_LABEL = {
    "aberta": "Aberta",
    "fechada": "Fechada (aguardando pagamento)",
    "parcial": "🟣 Parcialmente paga",
    "paga": "🟣 Paga",
}

# ---------------------------------------------------------------------
# Estado da página
# ---------------------------------------------------------------------
st.session_state.setdefault("cartao_editando_id", None)
st.session_state.setdefault("cartao_form_versao", 0)
st.session_state.setdefault("cartao_excluir_id", None)
st.session_state.setdefault("cartao_pagar_fatura_id", None)

mensagem = st.session_state.pop("cartao_mensagem", None)
if mensagem:
    st.success(mensagem)


def _definir_mensagem(texto: str) -> None:
    st.session_state["cartao_mensagem"] = texto


try:
    todas_contas = contas.listar_contas(incluir_inativas=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

mapa_contas = {c["id"]: c for c in todas_contas}


def nome_conta(conta_id: int | None) -> str:
    if conta_id is None:
        return "—"
    conta = mapa_contas.get(conta_id)
    if conta is None:
        return f"Conta #{conta_id}"
    return conta["nome"] if conta["ativa"] else f"{conta['nome']} (inativa)"


# ---------------------------------------------------------------------
# Formulário de criação/edição
# ---------------------------------------------------------------------
editando_id = st.session_state["cartao_editando_id"]
dados_edicao = cartoes.obter_cartao(editando_id) if editando_id is not None else None
if editando_id is not None and dados_edicao is None:
    st.session_state["cartao_editando_id"] = None
    editando_id = None

sufixo = (
    f"edit_{editando_id}_{st.session_state['cartao_form_versao']}"
    if editando_id
    else f"novo_{st.session_state['cartao_form_versao']}"
)

st.subheader(f"Editar cartão #{editando_id}" if editando_id else "Novo cartão")

col_a, col_b = st.columns(2)
with col_a:
    nome = st.text_input(
        "Nome", value=dados_edicao["nome"] if dados_edicao else "", key=f"cartao_nome_{sufixo}"
    )
with col_b:
    instituicao = st.text_input(
        "Instituição",
        value=(dados_edicao.get("instituicao") or "") if dados_edicao else "",
        key=f"cartao_instituicao_{sufixo}",
    )

col_c, col_d, col_e = st.columns(3)
with col_c:
    limite_texto = st.text_input(
        "Limite (R$)",
        value=str(dados_edicao["limite"]) if dados_edicao else "0",
        placeholder="Ex.: 5000,00",
        key=f"cartao_limite_{sufixo}",
    )
with col_d:
    dia_fechamento = st.number_input(
        "Dia de fechamento",
        min_value=1,
        max_value=31,
        step=1,
        format="%d",
        value=int(dados_edicao["dia_fechamento"]) if dados_edicao else 1,
        key=f"cartao_dia_fechamento_{sufixo}",
    )
with col_e:
    dia_vencimento = st.number_input(
        "Dia de vencimento",
        min_value=1,
        max_value=31,
        step=1,
        format="%d",
        value=int(dados_edicao["dia_vencimento"]) if dados_edicao else 10,
        key=f"cartao_dia_vencimento_{sufixo}",
    )

ids_conta_pagamento = [None] + [c["id"] for c in todas_contas if c["ativa"]]
conta_pagamento_default = dados_edicao["conta_pagamento_id"] if dados_edicao else None
if conta_pagamento_default not in ids_conta_pagamento:
    conta_pagamento_default = None
conta_pagamento_id = st.selectbox(
    "Conta de pagamento padrão (opcional)",
    ids_conta_pagamento,
    index=ids_conta_pagamento.index(conta_pagamento_default),
    format_func=lambda cid: "Nenhuma" if cid is None else nome_conta(cid),
    key=f"cartao_conta_pagamento_{sufixo}",
)

ativo = st.checkbox(
    "Ativo", value=dados_edicao["ativo"] if dados_edicao else True, key=f"cartao_ativo_{sufixo}"
)

col_salvar, col_cancelar = st.columns([1, 1])
with col_salvar:
    rotulo_botao = "Salvar edição" if editando_id else "Criar cartão"
    if st.button(rotulo_botao, type="primary", key=f"cartao_salvar_{sufixo}"):
        try:
            limite_decimal = texto_para_decimal(limite_texto)
            if editando_id:
                cartoes.atualizar_cartao(
                    editando_id,
                    nome=nome,
                    instituicao=instituicao or None,
                    limite=limite_decimal,
                    dia_fechamento=int(dia_fechamento),
                    dia_vencimento=int(dia_vencimento),
                    conta_pagamento_id=conta_pagamento_id,
                    ativo=ativo,
                )
                _definir_mensagem("Cartão atualizado com sucesso.")
            else:
                cartoes.criar_cartao(
                    nome=nome,
                    limite=limite_decimal,
                    dia_fechamento=int(dia_fechamento),
                    dia_vencimento=int(dia_vencimento),
                    instituicao=instituicao or None,
                    conta_pagamento_id=conta_pagamento_id,
                )
                _definir_mensagem("Cartão criado com sucesso.")
            st.session_state["cartao_editando_id"] = None
            st.session_state["cartao_form_versao"] += 1
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Ocorreu um erro inesperado ao salvar o cartão.")

if editando_id:
    with col_cancelar:
        if st.button("Cancelar edição", key=f"cartao_cancelar_{sufixo}"):
            st.session_state["cartao_editando_id"] = None
            st.session_state["cartao_form_versao"] += 1
            st.rerun()


# ---------------------------------------------------------------------
# Diálogo de confirmação de exclusão
# ---------------------------------------------------------------------
@st.dialog("Confirmar exclusão")
def _confirmar_exclusao(cartao_id: int) -> None:
    cartao = cartoes.obter_cartao(cartao_id)
    if cartao is None:
        st.warning("Este cartão já não existe mais.")
        if st.button("Fechar", key="cartao_confirmar_exclusao_fechar"):
            st.session_state["cartao_excluir_id"] = None
            st.rerun()
        return

    st.write(f"Tem certeza que deseja excluir o cartão **{cartao['nome']}**?")
    st.caption(
        "Se houver compras ou faturas vinculadas, o cartão será desativado em vez de excluído."
    )
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="cartao_confirmar_exclusao_sim"):
            try:
                cartoes.excluir_cartao(cartao_id)
                ainda_existe = cartoes.obter_cartao(cartao_id)
                if ainda_existe is None:
                    _definir_mensagem("Cartão excluído com sucesso.")
                else:
                    _definir_mensagem("Cartão possui movimentações vinculadas e foi desativado.")
                st.session_state["cartao_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="cartao_confirmar_exclusao_cancelar"):
            st.session_state["cartao_excluir_id"] = None
            st.rerun()


if st.session_state["cartao_excluir_id"] is not None:
    _confirmar_exclusao(st.session_state["cartao_excluir_id"])


# ---------------------------------------------------------------------
# Diálogo de registro de pagamento
# ---------------------------------------------------------------------
@st.dialog("Registrar pagamento de fatura")
def _registrar_pagamento(fatura_id: int) -> None:
    fatura = faturas.obter_fatura(fatura_id)
    if fatura is None:
        st.warning("Esta fatura já não existe mais.")
        if st.button("Fechar", key="pagamento_fechar"):
            st.session_state["cartao_pagar_fatura_id"] = None
            st.rerun()
        return

    cartao = cartoes.obter_cartao(fatura["cartao_id"])
    saldo_devedor = faturas.calcular_saldo_devedor_fatura(fatura_id)

    st.write(f"**Cartão:** {cartao['nome']}")
    st.write(f"**Fatura de:** {fatura['mes_referencia'].strftime('%m/%Y')}")
    st.write(f"**Saldo devedor:** {formatar_moeda(saldo_devedor)}")

    if saldo_devedor <= 0:
        st.info("Esta fatura já está totalmente paga.")
        if st.button("Fechar", key="pagamento_fechar_paga"):
            st.session_state["cartao_pagar_fatura_id"] = None
            st.rerun()
        return

    contas_ativas = [c for c in todas_contas if c["ativa"]]
    if not contas_ativas:
        st.warning("Cadastre uma conta ativa para registrar o pagamento.")
        return

    ids_conta_pg = [c["id"] for c in contas_ativas]
    conta_default = (
        cartao["conta_pagamento_id"] if cartao.get("conta_pagamento_id") in ids_conta_pg else ids_conta_pg[0]
    )
    conta_pagamento_escolhida = st.selectbox(
        "Pagar com a conta",
        ids_conta_pg,
        index=ids_conta_pg.index(conta_default),
        format_func=nome_conta,
        key="pagamento_conta",
    )
    valor_texto = st.text_input(
        "Valor do pagamento (R$)", value=str(saldo_devedor), key="pagamento_valor"
    )
    data_pagamento = st.date_input("Data do pagamento", value=date.today(), key="pagamento_data")

    if st.button("Confirmar pagamento", type="primary", key="pagamento_confirmar"):
        try:
            valor_decimal = texto_para_decimal(valor_texto)
            faturas.registrar_pagamento_fatura(
                fatura_id, conta_pagamento_escolhida, valor_decimal, data_pagamento
            )
            _definir_mensagem(f"{badge_pagamento_fatura()} registrado com sucesso.")
            st.session_state["cartao_pagar_fatura_id"] = None
            st.rerun()
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
    if st.button("Cancelar", key="pagamento_cancelar"):
        st.session_state["cartao_pagar_fatura_id"] = None
        st.rerun()


if st.session_state["cartao_pagar_fatura_id"] is not None:
    _registrar_pagamento(st.session_state["cartao_pagar_fatura_id"])


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------
st.divider()
st.subheader("Seus cartões")

mostrar_inativos = st.checkbox("Mostrar cartões inativos", value=True, key="cartao_mostrar_inativos")

try:
    lista_cartoes = cartoes.listar_cartoes(incluir_inativos=mostrar_inativos)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    lista_cartoes = []

if not lista_cartoes:
    st.info("Nenhum cartão cadastrado ainda. Use o formulário acima para criar o primeiro.")
else:
    hoje = date.today()
    for cartao in lista_cartoes:
        with st.container(border=True):
            titulo = cartao["nome"]
            if cartao.get("instituicao"):
                titulo += f" ({cartao['instituicao']})"
            if not cartao["ativo"]:
                titulo += " — inativo"
            st.markdown(f"### {titulo}")

            try:
                limite_utilizado = faturas.calcular_limite_utilizado(cartao["id"])
            except ErroBancoDeDados as exc:
                st.error(str(exc))
                limite_utilizado = None

            if limite_utilizado is not None:
                limite_disponivel = cartao["limite"] - limite_utilizado
                col_lim1, col_lim2, col_lim3 = st.columns(3)
                col_lim1.metric("Limite", formatar_moeda(cartao["limite"]))
                col_lim2.metric("Utilizado", formatar_moeda(limite_utilizado))
                col_lim3.metric("Disponível", formatar_moeda(limite_disponivel))

            st.caption(
                f"Fecha todo dia {cartao['dia_fechamento']} · "
                f"Vence todo dia {cartao['dia_vencimento']} · "
                f"Pagamento padrão: {nome_conta(cartao.get('conta_pagamento_id'))}"
            )

            todas_faturas = faturas.listar_faturas(cartao_id=cartao["id"])
            mes_referencia_atual = faturas.calcular_mes_referencia(cartao["dia_fechamento"], hoje)
            fatura_atual = next(
                (f for f in todas_faturas if f["mes_referencia"] == mes_referencia_atual), None
            )
            faturas_anteriores = [
                f for f in todas_faturas if f["mes_referencia"] != mes_referencia_atual
            ]

            st.markdown("**Fatura atual**")
            if fatura_atual is None:
                st.caption("Nenhuma compra lançada na fatura atual ainda.")
            else:
                total_atual = faturas.calcular_total_fatura(fatura_atual["id"])
                status_atual = faturas.status_exibicao_fatura(fatura_atual, hoje=hoje)
                saldo_devedor_atual = faturas.calcular_saldo_devedor_fatura(fatura_atual["id"])
                tipo_cor_atual = "pagamento_fatura" if status_atual in ("paga", "parcial") else None
                with container_linha_colorida(st, f"fatura_atual_{fatura_atual['id']}", tipo_cor_atual):
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                    col_f1.write(f"Mês: {fatura_atual['mes_referencia'].strftime('%m/%Y')}")
                    col_f2.write(f"Total: {formatar_moeda(total_atual)}")
                    col_f3.write(f"Vencimento: {fatura_atual['data_vencimento'].strftime('%d/%m/%Y')}")
                    col_f4.write(f"Status: {STATUS_LABEL.get(status_atual, status_atual)}")
                    if saldo_devedor_atual > 0:
                        if st.button(
                            "Registrar pagamento", key=f"cartao_pagar_atual_{cartao['id']}"
                        ):
                            st.session_state["cartao_pagar_fatura_id"] = fatura_atual["id"]
                            st.rerun()

            if faturas_anteriores:
                with st.expander(f"Ver faturas anteriores ({len(faturas_anteriores)})"):
                    for fatura_antiga in faturas_anteriores:
                        total_antiga = faturas.calcular_total_fatura(fatura_antiga["id"])
                        status_antiga = faturas.status_exibicao_fatura(fatura_antiga, hoje=hoje)
                        saldo_devedor_antiga = faturas.calcular_saldo_devedor_fatura(
                            fatura_antiga["id"]
                        )
                        tipo_cor_antiga = (
                            "pagamento_fatura" if status_antiga in ("paga", "parcial") else None
                        )
                        with container_linha_colorida(
                            st, f"fatura_antiga_{fatura_antiga['id']}", tipo_cor_antiga
                        ):
                            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
                            col_a1.write(fatura_antiga["mes_referencia"].strftime("%m/%Y"))
                            col_a2.write(formatar_moeda(total_antiga))
                            col_a3.write(fatura_antiga["data_vencimento"].strftime("%d/%m/%Y"))
                            col_a4.write(STATUS_LABEL.get(status_antiga, status_antiga))
                            if saldo_devedor_antiga > 0:
                                if col_a5.button(
                                    "Pagar", key=f"cartao_pagar_antiga_{fatura_antiga['id']}"
                                ):
                                    st.session_state["cartao_pagar_fatura_id"] = fatura_antiga["id"]
                                    st.rerun()

            col_1, col_2, col_3 = st.columns(3)
            if col_1.button("Editar", key=f"cartao_editar_{cartao['id']}"):
                st.session_state["cartao_editando_id"] = cartao["id"]
                st.session_state["cartao_form_versao"] += 1
                st.rerun()
            rotulo_toggle = "Desativar" if cartao["ativo"] else "Ativar"
            if col_2.button(rotulo_toggle, key=f"cartao_toggle_{cartao['id']}"):
                try:
                    cartoes.atualizar_cartao(cartao["id"], ativo=not cartao["ativo"])
                    st.rerun()
                except (ValueError, ErroBancoDeDados) as exc:
                    st.error(str(exc))
            if col_3.button("Excluir", key=f"cartao_excluir_{cartao['id']}"):
                st.session_state["cartao_excluir_id"] = cartao["id"]
                st.rerun()
