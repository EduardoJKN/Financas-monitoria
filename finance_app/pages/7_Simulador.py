import streamlit as st

from src import metas, simulador
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import formatar_moeda, texto_para_decimal

st.set_page_config(page_title="Simulador | Economia UaU", layout="wide")
st.title("Simulador")
st.caption("Projeções simples, sem considerar rendimento/juros nesta primeira versão.")

MODOS = {
    "Tempo para atingir meta": "tempo",
    "Aporte mensal necessário": "aporte",
    "Projeção de saldo": "projecao",
}

rotulo_modo = st.selectbox("Modo", list(MODOS.keys()), key="sim_modo")
modo = MODOS[rotulo_modo]

try:
    metas_disponiveis = metas.listar_metas()
except ErroBancoDeDados as exc:
    st.error(str(exc))
    metas_disponiveis = []


def _preencher_a_partir_da_meta(meta_id: int, chave_atual: str, chave_alvo: str) -> None:
    meta = next((m for m in metas_disponiveis if m["id"] == meta_id), None)
    if meta is None:
        return
    st.session_state[chave_atual] = str(meta["valor_atual"])
    st.session_state[chave_alvo] = str(meta["valor_alvo"])


# =======================================================================
# A. Tempo para atingir meta
# =======================================================================
if modo == "tempo":
    st.subheader("Tempo para atingir uma meta")

    if metas_disponiveis:
        col_meta, col_botao = st.columns([3, 1])
        with col_meta:
            meta_escolhida_id = st.selectbox(
                "Preencher a partir de uma meta existente (opcional)",
                [None] + [m["id"] for m in metas_disponiveis],
                format_func=lambda mid: "(nenhuma)" if mid is None else next(
                    m["nome"] for m in metas_disponiveis if m["id"] == mid
                ),
                key="sim_tempo_meta_escolhida",
            )
        with col_botao:
            st.write("")
            if meta_escolhida_id is not None and st.button(
                "Usar valores desta meta", key="sim_tempo_usar_meta"
            ):
                _preencher_a_partir_da_meta(
                    meta_escolhida_id, "sim_tempo_valor_atual", "sim_tempo_valor_alvo"
                )
                st.rerun()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        valor_atual_texto = st.text_input(
            "Valor atual (R$)", value="0", key="sim_tempo_valor_atual"
        )
    with col_b:
        valor_alvo_texto = st.text_input(
            "Valor alvo (R$)", value="0", key="sim_tempo_valor_alvo"
        )
    with col_c:
        aporte_texto = st.text_input(
            "Aporte mensal (R$)", value="0", key="sim_tempo_aporte"
        )

    if st.button("Calcular", type="primary", key="sim_tempo_calcular"):
        try:
            valor_atual = texto_para_decimal(valor_atual_texto)
            valor_alvo = texto_para_decimal(valor_alvo_texto)
            aporte_mensal = texto_para_decimal(aporte_texto)
            resultado = simulador.calcular_meses_para_meta(
                valor_atual, valor_alvo, aporte_mensal
            )
            if resultado["ja_atingida"]:
                st.success("Esta meta já foi atingida! 🎉")
            else:
                st.success(
                    f"Faltam **{resultado['meses']} mês(es)** "
                    f"({resultado['anos']} ano(s) e {resultado['meses_restantes']} mês(es))."
                )
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))

# =======================================================================
# B. Aporte mensal necessário
# =======================================================================
elif modo == "aporte":
    st.subheader("Aporte mensal necessário")

    if metas_disponiveis:
        col_meta, col_botao = st.columns([3, 1])
        with col_meta:
            meta_escolhida_id = st.selectbox(
                "Preencher a partir de uma meta existente (opcional)",
                [None] + [m["id"] for m in metas_disponiveis],
                format_func=lambda mid: "(nenhuma)" if mid is None else next(
                    m["nome"] for m in metas_disponiveis if m["id"] == mid
                ),
                key="sim_aporte_meta_escolhida",
            )
        with col_botao:
            st.write("")
            if meta_escolhida_id is not None and st.button(
                "Usar valores desta meta", key="sim_aporte_usar_meta"
            ):
                _preencher_a_partir_da_meta(
                    meta_escolhida_id, "sim_aporte_valor_atual", "sim_aporte_valor_alvo"
                )
                st.rerun()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        valor_atual_texto = st.text_input(
            "Valor atual (R$)", value="0", key="sim_aporte_valor_atual"
        )
    with col_b:
        valor_alvo_texto = st.text_input(
            "Valor alvo (R$)", value="0", key="sim_aporte_valor_alvo"
        )
    with col_c:
        meses_input = st.number_input(
            "Quantidade de meses", min_value=1, step=1, format="%d", key="sim_aporte_meses"
        )

    if st.button("Calcular", type="primary", key="sim_aporte_calcular"):
        try:
            valor_atual = texto_para_decimal(valor_atual_texto)
            valor_alvo = texto_para_decimal(valor_alvo_texto)
            resultado = simulador.calcular_aporte_necessario(
                valor_atual, valor_alvo, int(meses_input)
            )
            if resultado["ja_atingida"]:
                st.success("Esta meta já foi atingida! 🎉")
            else:
                st.success(
                    f"Aporte mensal necessário: **{formatar_moeda(resultado['aporte_mensal'])}**"
                )
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))

# =======================================================================
# C. Projeção de saldo
# =======================================================================
else:
    st.subheader("Projeção de saldo")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        saldo_inicial_texto = st.text_input(
            "Saldo inicial (R$)", value="0", key="sim_proj_saldo_inicial"
        )
    with col_b:
        aporte_texto = st.text_input(
            "Aporte mensal (R$)", value="0", key="sim_proj_aporte"
        )
    with col_c:
        meses_input = st.number_input(
            "Quantidade de meses", min_value=1, step=1, format="%d", key="sim_proj_meses"
        )

    if st.button("Calcular", type="primary", key="sim_proj_calcular"):
        try:
            saldo_inicial = texto_para_decimal(saldo_inicial_texto)
            aporte_mensal = texto_para_decimal(aporte_texto)
            resultado = simulador.projetar_saldo(saldo_inicial, aporte_mensal, int(meses_input))

            st.success(f"Saldo projetado ao final: **{formatar_moeda(resultado['saldo_final'])}**")

            st.write("Evolução mês a mês:")
            for item in resultado["evolucao"]:
                st.write(f"Mês {item['mes']}: {formatar_moeda(item['saldo'])}")
        except (ValueError, ErroBancoDeDados) as exc:
            st.error(str(exc))
