from datetime import date
from decimal import Decimal, InvalidOperation

import streamlit as st

from src import categorias, contas, transacoes
from src.banco_de_dados import ErroBancoDeDados

st.set_page_config(page_title="Lançamentos | Economia UaU", layout="wide")
st.title("Lançamentos")

TIPOS_LABEL = {"receita": "Receita", "despesa": "Despesa", "transferencia": "Transferência"}
TIPOS_INTERNO = {rotulo: interno for interno, rotulo in TIPOS_LABEL.items()}


def _texto_para_decimal(texto: str) -> Decimal:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Informe um valor.")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(
            f"Valor inválido: '{texto}'. Use um número, por exemplo 1234,56."
        ) from exc


def _formatar_valor(valor: Decimal) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


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
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

mapa_contas = {c["id"]: c for c in todas_contas}
mapa_categorias = {c["id"]: c for c in todas_categorias}


def nome_conta(conta_id: int | None) -> str:
    if conta_id is None:
        return "—"
    conta = mapa_contas.get(conta_id)
    if conta is None:
        return f"Conta #{conta_id}"
    return conta["nome"] if conta["ativa"] else f"{conta['nome']} (inativa)"


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

col_a, col_b = st.columns(2)
with col_a:
    descricao = st.text_input(
        "Descrição", value=dados_edicao["descricao"] if dados_edicao else "", key=f"descricao_{sufixo}"
    )
with col_b:
    valor_texto = st.text_input(
        "Valor (R$)",
        value=str(dados_edicao["valor"]) if dados_edicao else "",
        placeholder="Ex.: 1234,56",
        key=f"valor_{sufixo}",
    )

col_c, col_d = st.columns(2)
with col_c:
    data_transacao = st.date_input(
        "Data",
        value=dados_edicao["data_transacao"] if dados_edicao else date.today(),
        key=f"data_{sufixo}",
    )

conta_id: int | None = None
conta_destino_id: int | None = None
categoria_id: int | None = None

if tipo in ("receita", "despesa"):
    with col_d:
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

col_salvar, col_cancelar = st.columns([1, 1])
with col_salvar:
    rotulo_botao = "Salvar edição" if editando_id else "Criar lançamento"
    if st.button(rotulo_botao, type="primary", key=f"salvar_{sufixo}"):
        if conta_id is None:
            st.error("Cadastre uma conta ativa antes de criar lançamentos.")
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
        colunas[2].write(lancamento["descricao"])
        colunas[3].write(caminho_categoria(lancamento["categoria_id"]))
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
