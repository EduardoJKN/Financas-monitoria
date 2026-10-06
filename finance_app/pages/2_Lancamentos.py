from datetime import date
from decimal import Decimal

import streamlit as st

from src import cartoes, categorias, contas, recorrencias, transacoes
from src.banco_de_dados import ErroBancoDeDados
from src.formatacao import badge_tipo_transacao, formatar_moeda, texto_para_decimal

st.title("Lançamentos")

TIPOS_LABEL = {t: badge_tipo_transacao(t) for t in ("receita", "despesa", "transferencia")}
TIPOS_INTERNO = {rotulo: interno for interno, rotulo in TIPOS_LABEL.items()}
_texto_para_decimal = texto_para_decimal
_formatar_valor = formatar_moeda


# ---------------------------------------------------------------------
# Estado da página
# ---------------------------------------------------------------------
st.session_state.setdefault("lanc_editando_id", None)
st.session_state.setdefault("lanc_form_versao", 0)
st.session_state.setdefault("lanc_excluir_id", None)

mensagem = st.session_state.pop("lanc_mensagem", None)
if mensagem:
    st.success(mensagem)


def _definir_mensagem(texto: str) -> None:
    st.session_state["lanc_mensagem"] = texto


# ---------------------------------------------------------------------
# Dados auxiliares (contas e categorias já cadastradas)
# ---------------------------------------------------------------------
try:
    todas_contas = contas.listar_contas(incluir_inativas=True)
    todas_categorias = categorias.listar_categorias(incluir_inativas=True)
    todos_cartoes = cartoes.listar_cartoes(incluir_inativos=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

mapa_contas = {c["id"]: c for c in todas_contas}
mapa_categorias = {c["id"]: c for c in todas_categorias}
mapa_cartoes = {c["id"]: c for c in todos_cartoes}


def nome_conta(conta_id: int | None) -> str:
    if conta_id is None:
        return "—"
    conta = mapa_contas.get(conta_id)
    if conta is None:
        return f"Conta #{conta_id}"
    return conta["nome"] if conta["ativa"] else f"{conta['nome']} (inativa)"


def nome_cartao(cartao_id: int | None) -> str:
    if cartao_id is None:
        return "—"
    cartao = mapa_cartoes.get(cartao_id)
    if cartao is None:
        return f"Cartão #{cartao_id}"
    return cartao["nome"] if cartao["ativo"] else f"{cartao['nome']} (inativo)"


def opcoes_cartoes_ativos(incluir_extra_id: int | None = None) -> list[int]:
    ids = [c["id"] for c in todos_cartoes if c["ativo"]]
    if incluir_extra_id is not None and incluir_extra_id not in ids and incluir_extra_id in mapa_cartoes:
        ids.append(incluir_extra_id)
    return ids


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
        rotulo = categoria["nome"] if categoria["ativa"] else f"{categoria['nome']} (inativa)"
        partes.append(rotulo)
        atual_id = categoria["categoria_pai_id"]
    return " > ".join(reversed(partes)) if partes else "—"


def opcoes_contas_ativas(incluir_extra_id: int | None = None) -> list[int]:
    ids = [c["id"] for c in todas_contas if c["ativa"]]
    if incluir_extra_id is not None and incluir_extra_id not in ids and incluir_extra_id in mapa_contas:
        ids.append(incluir_extra_id)
    return ids


def opcoes_categorias_para_tipo(tipo_transacao: str, incluir_extra_id: int | None = None) -> list[int]:
    tipos_aceitos = {"receita", "ambos"} if tipo_transacao == "receita" else {"despesa", "ambos"}
    ids = [c["id"] for c in todas_categorias if c["ativa"] and c["tipo"] in tipos_aceitos]
    if incluir_extra_id is not None and incluir_extra_id not in ids and incluir_extra_id in mapa_categorias:
        ids.append(incluir_extra_id)
    return ids


# ---------------------------------------------------------------------
# Formulário de criação/edição
# ---------------------------------------------------------------------
editando_id = st.session_state["lanc_editando_id"]
dados_edicao = transacoes.obter_transacao(editando_id) if editando_id is not None else None
if editando_id is not None and dados_edicao is None:
    # a transação pode ter sido excluída em outra aba/sessão
    st.session_state["lanc_editando_id"] = None
    editando_id = None

sufixo = f"edit_{editando_id}_{st.session_state['lanc_form_versao']}" if editando_id else f"novo_{st.session_state['lanc_form_versao']}"

st.subheader(f"Editar lançamento #{editando_id}" if editando_id else "Novo lançamento")

rotulos_tipo = list(TIPOS_LABEL.values())
tipo_default = TIPOS_LABEL[dados_edicao["tipo"]] if dados_edicao else rotulos_tipo[0]
tipo_label = st.selectbox(
    "Tipo", rotulos_tipo, index=rotulos_tipo.index(tipo_default), key=f"tipo_{sufixo}"
)
tipo = TIPOS_INTERNO[tipo_label]

parcelado = False
if tipo in ("receita", "despesa") and not editando_id:
    modo_label = st.radio(
        "Forma de lançamento", ["À vista", "Parcelado"], horizontal=True, key=f"modo_{sufixo}"
    )
    parcelado = modo_label == "Parcelado"

col_a, col_b = st.columns(2)
with col_a:
    descricao = st.text_input(
        "Descrição", value=dados_edicao["descricao"] if dados_edicao else "", key=f"descricao_{sufixo}"
    )
with col_b:
    valor_texto = st.text_input(
        "Valor total (R$)" if parcelado else "Valor (R$)",
        value=str(dados_edicao["valor"]) if dados_edicao else "",
        placeholder="Ex.: 1234,56",
        key=f"valor_{sufixo}",
    )

col_c, col_d = st.columns(2)
with col_c:
    data_transacao = st.date_input(
        "Data da 1ª parcela" if parcelado else "Data",
        value=dados_edicao["data_transacao"] if dados_edicao else date.today(),
        key=f"data_{sufixo}",
    )

quantidade_parcelas = 2
if parcelado:
    quantidade_parcelas = st.number_input(
        "Quantidade de parcelas",
        min_value=2,
        step=1,
        format="%d",
        key=f"qtd_parcelas_{sufixo}",
    )

conta_id: int | None = None
cartao_id: int | None = None
conta_destino_id: int | None = None
categoria_id: int | None = None
forma_pagamento = "conta"

if tipo in ("receita", "despesa"):
    if tipo == "despesa":
        rotulos_forma = ["Conta", "Cartão de crédito"]
        forma_default = (
            "Cartão de crédito" if dados_edicao and dados_edicao.get("cartao_id") else "Conta"
        )
        forma_label = st.radio(
            "Forma de pagamento",
            rotulos_forma,
            index=rotulos_forma.index(forma_default),
            horizontal=True,
            key=f"forma_pg_{sufixo}",
        )
        forma_pagamento = "cartao" if forma_label == "Cartão de crédito" else "conta"

    with col_d:
        if forma_pagamento == "cartao":
            ids_cartao = opcoes_cartoes_ativos(dados_edicao["cartao_id"] if dados_edicao else None)
            if ids_cartao:
                cartao_default = dados_edicao["cartao_id"] if dados_edicao else ids_cartao[0]
                indice_cartao = (
                    ids_cartao.index(cartao_default) if cartao_default in ids_cartao else 0
                )
                cartao_id = st.selectbox(
                    "Cartão",
                    ids_cartao,
                    index=indice_cartao,
                    format_func=nome_cartao,
                    key=f"cartao_{sufixo}",
                )
            else:
                st.warning("Nenhum cartão ativo cadastrado. Cadastre um na página Cartões.")
        else:
            ids_conta = opcoes_contas_ativas(dados_edicao["conta_id"] if dados_edicao else None)
            if ids_conta:
                conta_default = dados_edicao["conta_id"] if dados_edicao else ids_conta[0]
                indice = ids_conta.index(conta_default) if conta_default in ids_conta else 0
                conta_id = st.selectbox(
                    "Conta", ids_conta, index=indice, format_func=nome_conta, key=f"conta_{sufixo}"
                )
            else:
                st.warning("Nenhuma conta ativa cadastrada.")

    ids_categoria = opcoes_categorias_para_tipo(
        tipo, dados_edicao["categoria_id"] if dados_edicao else None
    )
    opcoes_categoria = [None] + ids_categoria
    categoria_default = dados_edicao["categoria_id"] if dados_edicao else None
    indice_categoria = (
        opcoes_categoria.index(categoria_default) if categoria_default in opcoes_categoria else 0
    )
    categoria_id = st.selectbox(
        "Categoria",
        opcoes_categoria,
        index=indice_categoria,
        format_func=lambda cid: "Sem categoria" if cid is None else caminho_categoria(cid),
        key=f"categoria_{sufixo}",
    )
else:  # transferencia
    with col_d:
        ids_origem = opcoes_contas_ativas(dados_edicao["conta_id"] if dados_edicao else None)
        if ids_origem:
            origem_default = dados_edicao["conta_id"] if dados_edicao else ids_origem[0]
            indice_origem = ids_origem.index(origem_default) if origem_default in ids_origem else 0
            conta_id = st.selectbox(
                "Conta de origem",
                ids_origem,
                index=indice_origem,
                format_func=nome_conta,
                key=f"conta_origem_{sufixo}",
            )
        else:
            st.warning("Nenhuma conta ativa cadastrada.")

    ids_destino_base = opcoes_contas_ativas(
        dados_edicao["conta_destino_id"] if dados_edicao else None
    )
    ids_destino = [cid for cid in ids_destino_base if cid != conta_id]
    if ids_destino:
        destino_default = dados_edicao["conta_destino_id"] if dados_edicao else None
        indice_destino = ids_destino.index(destino_default) if destino_default in ids_destino else 0
        conta_destino_id = st.selectbox(
            "Conta de destino",
            ids_destino,
            index=indice_destino,
            format_func=nome_conta,
            key=f"conta_destino_{sufixo}",
        )
    else:
        st.warning("Cadastre outra conta ativa para habilitar transferências.")

observacao = st.text_area(
    "Observação",
    value=(dados_edicao.get("observacao") or "") if dados_edicao else "",
    key=f"observacao_{sufixo}",
)

pagamento_valido = (
    cartao_id is not None if (tipo == "despesa" and forma_pagamento == "cartao") else conta_id is not None
)

col_salvar, col_cancelar = st.columns([1, 1])
if not parcelado:
    with col_salvar:
        rotulo_botao = "Salvar edição" if editando_id else "Criar lançamento"
        if st.button(rotulo_botao, type="primary", key=f"salvar_{sufixo}"):
            if not pagamento_valido:
                st.error("Selecione uma conta ou cartão ativo antes de criar lançamentos.")
            elif tipo == "transferencia" and conta_destino_id is None and ids_destino_base and len(ids_destino_base) > 1:
                st.error("Selecione a conta de destino da transferência.")
            else:
                try:
                    valor_decimal = _texto_para_decimal(valor_texto)
                    categoria_final = categoria_id if tipo in ("receita", "despesa") else None
                    destino_final = conta_destino_id if tipo == "transferencia" else None
                    if editando_id:
                        transacoes.atualizar_transacao(
                            editando_id,
                            tipo=tipo,
                            descricao=descricao,
                            valor=valor_decimal,
                            data_transacao=data_transacao,
                            conta_id=conta_id,
                            cartao_id=cartao_id,
                            conta_destino_id=destino_final,
                            categoria_id=categoria_final,
                            observacao=observacao or None,
                        )
                        _definir_mensagem("Lançamento atualizado com sucesso.")
                    else:
                        transacoes.criar_transacao(
                            tipo=tipo,
                            descricao=descricao,
                            valor=valor_decimal,
                            data_transacao=data_transacao,
                            conta_id=conta_id,
                            cartao_id=cartao_id,
                            conta_destino_id=destino_final,
                            categoria_id=categoria_final,
                            origem="manual",
                            observacao=observacao or None,
                        )
                        _definir_mensagem("Lançamento criado com sucesso.")
                    st.session_state["lanc_editando_id"] = None
                    st.session_state["lanc_form_versao"] += 1
                    st.rerun()
                except (ValueError, ErroBancoDeDados) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Ocorreu um erro inesperado ao salvar o lançamento.")

if editando_id:
    with col_cancelar:
        if st.button("Cancelar edição", key=f"cancelar_{sufixo}"):
            st.session_state["lanc_editando_id"] = None
            st.session_state["lanc_form_versao"] += 1
            st.rerun()

if parcelado:
    st.markdown("**Prévia das parcelas**")
    try:
        valor_total_decimal = _texto_para_decimal(valor_texto) if valor_texto.strip() else None
    except ValueError:
        valor_total_decimal = None

    if not pagamento_valido:
        st.warning("Selecione uma conta ou cartão ativo antes de criar lançamentos parcelados.")
    elif valor_total_decimal is None:
        st.info("Informe um valor total válido para ver a prévia das parcelas.")
    else:
        try:
            preview = transacoes.simular_parcelas(
                valor_total_decimal, data_transacao, int(quantidade_parcelas)
            )
        except ValueError as exc:
            st.error(str(exc))
            preview = []

        if preview:
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.markdown("**Parcela**")
            col_p2.markdown("**Data**")
            col_p3.markdown("**Valor**")
            for item in preview:
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.write(f"{item['numero_parcela']}/{int(quantidade_parcelas)}")
                col_p2.write(item["data"].strftime("%d/%m/%Y"))
                col_p3.write(_formatar_valor(item["valor"]))

            soma_parcelas = sum((item["valor"] for item in preview), Decimal("0"))
            st.caption(
                f"Soma das parcelas: {_formatar_valor(soma_parcelas)} "
                f"(valor total: {_formatar_valor(valor_total_decimal)})"
            )

            if st.button(
                "Confirmar parcelamento", type="primary", key=f"confirmar_parcelamento_{sufixo}"
            ):
                try:
                    transacoes.criar_transacao_parcelada(
                        tipo=tipo,
                        descricao=descricao,
                        valor_total=valor_total_decimal,
                        data_primeira_parcela=data_transacao,
                        total_parcelas=int(quantidade_parcelas),
                        conta_id=conta_id,
                        cartao_id=cartao_id,
                        categoria_id=categoria_id,
                        observacao=observacao or None,
                        origem="manual",
                    )
                    _definir_mensagem(
                        f"Parcelamento criado com sucesso ({int(quantidade_parcelas)} parcelas)."
                    )
                    st.session_state["lanc_form_versao"] += 1
                    st.rerun()
                except (ValueError, ErroBancoDeDados) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Ocorreu um erro inesperado ao salvar o parcelamento.")


# ---------------------------------------------------------------------
# Diálogo de confirmação de exclusão
# ---------------------------------------------------------------------
@st.dialog("Confirmar exclusão")
def _confirmar_exclusao(transacao_id: int) -> None:
    transacao = transacoes.obter_transacao(transacao_id)
    if transacao is None:
        st.warning("Este lançamento já não existe mais.")
        if st.button("Fechar", key="confirmar_exclusao_fechar"):
            st.session_state["lanc_excluir_id"] = None
            st.rerun()
        return

    st.write(
        f"Tem certeza que deseja excluir o lançamento **{transacao['descricao']}** "
        f"de {_formatar_valor(transacao['valor'])}?"
    )
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="confirmar_exclusao_sim"):
            try:
                transacoes.excluir_transacao(transacao_id)
                st.session_state["lanc_excluir_id"] = None
                _definir_mensagem("Lançamento excluído com sucesso.")
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="confirmar_exclusao_cancelar"):
            st.session_state["lanc_excluir_id"] = None
            st.rerun()


if st.session_state["lanc_excluir_id"] is not None:
    _confirmar_exclusao(st.session_state["lanc_excluir_id"])


# ---------------------------------------------------------------------
# Filtros e listagem
# ---------------------------------------------------------------------
st.divider()
st.subheader("Histórico de lançamentos")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    filtro_tipo_label = st.selectbox("Tipo", ["Todos"] + rotulos_tipo, key="filtro_tipo")
with col_f2:
    opcoes_conta_filtro = [("Todas", None)] + [(nome_conta(c["id"]), c["id"]) for c in todas_contas]
    filtro_conta_label = st.selectbox(
        "Conta", [rotulo for rotulo, _ in opcoes_conta_filtro], key="filtro_conta"
    )
with col_f3:
    opcoes_categoria_filtro = [("Todas", None)] + [
        (caminho_categoria(c["id"]), c["id"]) for c in todas_categorias
    ]
    filtro_categoria_label = st.selectbox(
        "Categoria", [rotulo for rotulo, _ in opcoes_categoria_filtro], key="filtro_categoria"
    )

col_f4, col_f5 = st.columns(2)
with col_f4:
    filtro_data_inicial = st.date_input("Data inicial", value=None, key="filtro_data_inicial")
with col_f5:
    filtro_data_final = st.date_input("Data final", value=None, key="filtro_data_final")

filtro_texto = st.text_input("Buscar na descrição", key="filtro_texto")

mapa_label_conta = dict(opcoes_conta_filtro)
mapa_label_categoria = dict(opcoes_categoria_filtro)

filtro_tipo = TIPOS_INTERNO.get(filtro_tipo_label)
filtro_conta_id = mapa_label_conta.get(filtro_conta_label)
filtro_categoria_id = mapa_label_categoria.get(filtro_categoria_label)

try:
    lancamentos = transacoes.listar_transacoes(
        tipo=filtro_tipo,
        conta_id=filtro_conta_id,
        categoria_id=filtro_categoria_id,
        data_inicial=filtro_data_inicial,
        data_final=filtro_data_final,
        texto_busca=filtro_texto or None,
    )
except (ValueError, ErroBancoDeDados) as exc:
    st.error(str(exc))
    lancamentos = []

if not lancamentos:
    st.info("Nenhum lançamento encontrado para os filtros selecionados.")
else:
    larguras = [1, 1, 2, 2, 2, 2, 1, 1, 1]
    titulos = [
        "Data", "Tipo", "Descrição", "Categoria", "Conta", "Conta destino", "Valor", "", ""
    ]
    for coluna, titulo in zip(st.columns(larguras), titulos):
        if titulo:
            coluna.markdown(f"**{titulo}**")

    for lancamento in lancamentos:
        colunas = st.columns(larguras)
        colunas[0].write(lancamento["data_transacao"].strftime("%d/%m/%Y"))
        colunas[1].write(TIPOS_LABEL[lancamento["tipo"]])
        descricao_exibida = lancamento["descricao"]
        if lancamento.get("numero_parcela") and lancamento.get("total_parcelas"):
            descricao_exibida = (
                f"{descricao_exibida} — {lancamento['numero_parcela']}/{lancamento['total_parcelas']}"
            )
        colunas[2].write(descricao_exibida)
        colunas[3].write(caminho_categoria(lancamento["categoria_id"]))
        if lancamento.get("cartao_id"):
            colunas[4].write(f"💳 {nome_cartao(lancamento['cartao_id'])}")
        else:
            colunas[4].write(nome_conta(lancamento["conta_id"]))
        colunas[5].write(nome_conta(lancamento["conta_destino_id"]))
        colunas[6].write(_formatar_valor(lancamento["valor"]))
        if colunas[7].button("Editar", key=f"editar_{lancamento['id']}"):
            st.session_state["lanc_editando_id"] = lancamento["id"]
            st.session_state["lanc_form_versao"] += 1
            st.rerun()
        if colunas[8].button("Excluir", key=f"excluir_{lancamento['id']}"):
            st.session_state["lanc_excluir_id"] = lancamento["id"]
            st.rerun()


# =======================================================================
# Lançamentos recorrentes
# =======================================================================
st.divider()
st.header("Lançamentos recorrentes")
st.caption("Aluguel, salário, academia... lançamentos que se repetem automaticamente.")

PERIODICIDADE_LABEL = {"mensal": "Mensal", "semanal": "Semanal", "anual": "Anual"}
PERIODICIDADE_INTERNO = {rotulo: interno for interno, rotulo in PERIODICIDADE_LABEL.items()}

st.session_state.setdefault("rec_editando_id", None)
st.session_state.setdefault("rec_form_versao", 0)
st.session_state.setdefault("rec_excluir_id", None)

mensagem_rec = st.session_state.pop("rec_mensagem", None)
if mensagem_rec:
    st.success(mensagem_rec)


def _definir_mensagem_rec(texto: str) -> None:
    st.session_state["rec_mensagem"] = texto


try:
    todas_recorrencias = recorrencias.listar_recorrencias(incluir_inativas=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    todas_recorrencias = []

rec_editando_id = st.session_state["rec_editando_id"]
rec_dados_edicao = (
    recorrencias.obter_recorrencia(rec_editando_id) if rec_editando_id is not None else None
)
if rec_editando_id is not None and rec_dados_edicao is None:
    st.session_state["rec_editando_id"] = None
    rec_editando_id = None

rec_sufixo = (
    f"edit_{rec_editando_id}_{st.session_state['rec_form_versao']}"
    if rec_editando_id
    else f"novo_{st.session_state['rec_form_versao']}"
)

st.subheader(f"Editar recorrência #{rec_editando_id}" if rec_editando_id else "Nova recorrência")

col_r1, col_r2 = st.columns(2)
with col_r1:
    rotulos_tipo_rec = [TIPOS_LABEL["receita"], TIPOS_LABEL["despesa"]]
    tipo_rec_default = (
        TIPOS_LABEL[rec_dados_edicao["tipo"]] if rec_dados_edicao else rotulos_tipo_rec[0]
    )
    tipo_rec_label = st.selectbox(
        "Tipo",
        rotulos_tipo_rec,
        index=rotulos_tipo_rec.index(tipo_rec_default),
        key=f"rec_tipo_{rec_sufixo}",
    )
    tipo_rec = TIPOS_INTERNO[tipo_rec_label]
with col_r2:
    descricao_rec = st.text_input(
        "Descrição",
        value=rec_dados_edicao["descricao"] if rec_dados_edicao else "",
        placeholder="Ex.: Aluguel mensal",
        key=f"rec_descricao_{rec_sufixo}",
    )

col_r3, col_r4 = st.columns(2)
with col_r3:
    valor_rec_texto = st.text_input(
        "Valor (R$)",
        value=str(rec_dados_edicao["valor"]) if rec_dados_edicao else "",
        placeholder="Ex.: 1500,00",
        key=f"rec_valor_{rec_sufixo}",
    )
with col_r4:
    ids_conta_rec = opcoes_contas_ativas(rec_dados_edicao["conta_id"] if rec_dados_edicao else None)
    if ids_conta_rec:
        conta_rec_default = rec_dados_edicao["conta_id"] if rec_dados_edicao else ids_conta_rec[0]
        indice_conta_rec = (
            ids_conta_rec.index(conta_rec_default) if conta_rec_default in ids_conta_rec else 0
        )
        conta_id_rec = st.selectbox(
            "Conta",
            ids_conta_rec,
            index=indice_conta_rec,
            format_func=nome_conta,
            key=f"rec_conta_{rec_sufixo}",
        )
    else:
        st.warning("Nenhuma conta ativa cadastrada.")
        conta_id_rec = None

ids_categoria_rec = opcoes_categorias_para_tipo(
    tipo_rec, rec_dados_edicao["categoria_id"] if rec_dados_edicao else None
)
opcoes_categoria_rec = [None] + ids_categoria_rec
categoria_rec_default = rec_dados_edicao["categoria_id"] if rec_dados_edicao else None
indice_categoria_rec = (
    opcoes_categoria_rec.index(categoria_rec_default)
    if categoria_rec_default in opcoes_categoria_rec
    else 0
)
categoria_id_rec = st.selectbox(
    "Categoria",
    opcoes_categoria_rec,
    index=indice_categoria_rec,
    format_func=lambda cid: "Sem categoria" if cid is None else caminho_categoria(cid),
    key=f"rec_categoria_{rec_sufixo}",
)

col_r5, col_r6, col_r7 = st.columns(3)
with col_r5:
    rotulos_periodicidade = list(PERIODICIDADE_LABEL.values())
    periodicidade_default = (
        PERIODICIDADE_LABEL[rec_dados_edicao["periodicidade"]]
        if rec_dados_edicao
        else rotulos_periodicidade[0]
    )
    periodicidade_label = st.selectbox(
        "Periodicidade",
        rotulos_periodicidade,
        index=rotulos_periodicidade.index(periodicidade_default),
        key=f"rec_periodicidade_{rec_sufixo}",
    )
    periodicidade_rec = PERIODICIDADE_INTERNO[periodicidade_label]
with col_r6:
    data_inicio_rec = st.date_input(
        "Data de início",
        value=rec_dados_edicao["data_inicio"] if rec_dados_edicao else date.today(),
        key=f"rec_data_inicio_{rec_sufixo}",
    )
with col_r7:
    tem_data_fim_default = bool(rec_dados_edicao and rec_dados_edicao.get("data_fim"))
    tem_data_fim = st.checkbox(
        "Tem data final?", value=tem_data_fim_default, key=f"rec_tem_fim_{rec_sufixo}"
    )
    data_fim_rec = None
    if tem_data_fim:
        data_fim_rec = st.date_input(
            "Data final",
            value=(
                rec_dados_edicao["data_fim"]
                if rec_dados_edicao and rec_dados_edicao.get("data_fim")
                else date.today()
            ),
            key=f"rec_data_fim_{rec_sufixo}",
        )

observacao_rec = st.text_input(
    "Observação",
    value=(rec_dados_edicao.get("observacao") or "") if rec_dados_edicao else "",
    key=f"rec_observacao_{rec_sufixo}",
)

col_rec_salvar, col_rec_cancelar = st.columns([1, 1])
with col_rec_salvar:
    rotulo_botao_rec = "Salvar edição" if rec_editando_id else "Criar recorrência"
    if st.button(rotulo_botao_rec, type="primary", key=f"rec_salvar_{rec_sufixo}"):
        if conta_id_rec is None:
            st.error("Cadastre uma conta ativa antes de criar recorrências.")
        else:
            try:
                valor_rec_decimal = texto_para_decimal(valor_rec_texto)
                if rec_editando_id:
                    recorrencias.atualizar_recorrencia(
                        rec_editando_id,
                        tipo=tipo_rec,
                        descricao=descricao_rec,
                        valor=valor_rec_decimal,
                        conta_id=conta_id_rec,
                        categoria_id=categoria_id_rec,
                        periodicidade=periodicidade_rec,
                        data_inicio=data_inicio_rec,
                        data_fim=data_fim_rec,
                        observacao=observacao_rec or None,
                    )
                    _definir_mensagem_rec("Recorrência atualizada com sucesso.")
                else:
                    recorrencias.criar_recorrencia(
                        tipo=tipo_rec,
                        descricao=descricao_rec,
                        valor=valor_rec_decimal,
                        conta_id=conta_id_rec,
                        periodicidade=periodicidade_rec,
                        data_inicio=data_inicio_rec,
                        categoria_id=categoria_id_rec,
                        observacao=observacao_rec or None,
                        data_fim=data_fim_rec,
                    )
                    _definir_mensagem_rec("Recorrência criada com sucesso.")
                st.session_state["rec_editando_id"] = None
                st.session_state["rec_form_versao"] += 1
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Ocorreu um erro inesperado ao salvar a recorrência.")

if rec_editando_id:
    with col_rec_cancelar:
        if st.button("Cancelar edição", key=f"rec_cancelar_{rec_sufixo}"):
            st.session_state["rec_editando_id"] = None
            st.session_state["rec_form_versao"] += 1
            st.rerun()


@st.dialog("Confirmar exclusão")
def _confirmar_exclusao_rec(recorrencia_id: int) -> None:
    recorrencia = recorrencias.obter_recorrencia(recorrencia_id)
    if recorrencia is None:
        st.warning("Esta recorrência já não existe mais.")
        if st.button("Fechar", key="rec_confirmar_exclusao_fechar"):
            st.session_state["rec_excluir_id"] = None
            st.rerun()
        return

    st.write(f"Tem certeza que deseja excluir a recorrência **{recorrencia['descricao']}**?")
    st.caption("Se já houver lançamentos gerados por ela, será desativada em vez de excluída.")
    col_sim, col_nao = st.columns(2)
    with col_sim:
        if st.button("Sim, excluir", type="primary", key="rec_confirmar_exclusao_sim"):
            try:
                recorrencias.excluir_recorrencia(recorrencia_id)
                _definir_mensagem_rec("Recorrência removida com sucesso.")
                st.session_state["rec_excluir_id"] = None
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
    with col_nao:
        if st.button("Cancelar", key="rec_confirmar_exclusao_cancelar"):
            st.session_state["rec_excluir_id"] = None
            st.rerun()


if st.session_state["rec_excluir_id"] is not None:
    _confirmar_exclusao_rec(st.session_state["rec_excluir_id"])


st.divider()
col_gerar, col_info = st.columns([1, 3])
with col_gerar:
    if st.button("Gerar lançamentos recorrentes pendentes", type="primary", key="rec_gerar_pendentes"):
        try:
            resumo_geracao = recorrencias.gerar_lancamentos_pendentes()
            if resumo_geracao["total_gerado"] == 0:
                st.info("Nenhum lançamento pendente para gerar.")
            else:
                st.success(
                    f"{resumo_geracao['total_gerado']} lançamento(s) gerado(s) com sucesso."
                )
            st.rerun()
        except ErroBancoDeDados as exc:
            st.error(str(exc))

st.subheader("Recorrências cadastradas")
mostrar_inativas_rec = st.checkbox("Mostrar inativas", value=True, key="rec_mostrar_inativas")
lista_recorrencias = [r for r in todas_recorrencias if mostrar_inativas_rec or r["ativa"]]

if not lista_recorrencias:
    st.info("Nenhuma recorrência cadastrada ainda.")
else:
    larguras_rec = [2, 1, 1, 2, 1, 1, 1, 1, 1]
    titulos_rec = [
        "Descrição", "Tipo", "Valor", "Próxima data", "Periodicidade", "Ativa", "", "", ""
    ]
    for coluna, titulo in zip(st.columns(larguras_rec), titulos_rec):
        if titulo:
            coluna.markdown(f"**{titulo}**")

    for recorrencia in lista_recorrencias:
        colunas = st.columns(larguras_rec)
        colunas[0].write(recorrencia["descricao"])
        colunas[1].write(TIPOS_LABEL[recorrencia["tipo"]])
        colunas[2].write(formatar_moeda(recorrencia["valor"]))
        colunas[3].write(recorrencia["proxima_data"].strftime("%d/%m/%Y"))
        colunas[4].write(PERIODICIDADE_LABEL.get(recorrencia["periodicidade"], recorrencia["periodicidade"]))
        colunas[5].write("✅" if recorrencia["ativa"] else "⛔")
        if colunas[6].button("Editar", key=f"rec_editar_{recorrencia['id']}"):
            st.session_state["rec_editando_id"] = recorrencia["id"]
            st.session_state["rec_form_versao"] += 1
            st.rerun()
        rotulo_toggle_rec = "Desativar" if recorrencia["ativa"] else "Ativar"
        if colunas[7].button(rotulo_toggle_rec, key=f"rec_toggle_{recorrencia['id']}"):
            try:
                recorrencias.atualizar_recorrencia(recorrencia["id"], ativa=not recorrencia["ativa"])
                st.rerun()
            except (ValueError, ErroBancoDeDados) as exc:
                st.error(str(exc))
        if colunas[8].button("Excluir", key=f"rec_excluir_{recorrencia['id']}"):
            st.session_state["rec_excluir_id"] = recorrencia["id"]
            st.rerun()
