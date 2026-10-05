import hashlib
import io

import pandas as pd
import streamlit as st

from src import categorias as categorias_modulo
from src import categorizador, contas, importador, transacoes
from src.banco_de_dados import ErroBancoDeDados
from src.categorizador import normalizar_texto
from src.formatacao import formatar_moeda

st.set_page_config(page_title="Importação | Economia UaU", layout="wide")
st.title("Importação")
st.caption(
    "Importação de extratos em CSV. Nada é salvo até você confirmar a importação "
    "no final desta página."
)

DELIMITADORES_CANDIDATOS = importador.DELIMITADORES_CANDIDATOS
ENCODINGS_CANDIDATOS = importador.ENCODINGS_CANDIDATOS
ROTULOS_DELIMITADOR = {",": ",", ";": ";", "\t": "Tabulação", "|": "|"}

TIPO_MAPEAMENTO_OPCOES = {
    "Receita": "receita",
    "Despesa": "despesa",
    "Não importar (transferência/outro)": None,
}

STATUS_LABEL = {
    "ok": "✅",
    "duplicada": "⚠️",
    "revisar": "❓",
    "erro": "⛔",
}

# =======================================================================
# 1. Seleção e leitura do arquivo
# =======================================================================
arquivo = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

if arquivo is None:
    st.info("Selecione um arquivo CSV para iniciar a importação.")
    st.stop()

conteudo_bytes = arquivo.getvalue()
if not conteudo_bytes or not conteudo_bytes.strip():
    st.error("O arquivo está vazio.")
    st.stop()

hash_arquivo = hashlib.sha256(conteudo_bytes).hexdigest()[:12]

if st.session_state.get("imp_hash_arquivo") != hash_arquivo:
    for chave in list(st.session_state.keys()):
        if chave.startswith(("imp_sel_", "imp_cat_", "imp_tipomap_")):
            del st.session_state[chave]
    st.session_state["imp_hash_arquivo"] = hash_arquivo

encoding_detectado = importador.detectar_encoding(conteudo_bytes)
if encoding_detectado is None:
    st.error(
        "Não foi possível identificar a codificação do arquivo. "
        "Salve o CSV em UTF-8 e tente novamente."
    )
    st.stop()

texto_arquivo = conteudo_bytes.decode(encoding_detectado)
if not texto_arquivo.strip():
    st.error("O arquivo está vazio.")
    st.stop()

delimitador_detectado = importador.detectar_delimitador(texto_arquivo) or ","
cabecalho_detectado = importador.detectar_cabecalho(texto_arquivo)

st.subheader("1. Leitura do arquivo")
col1, col2, col3 = st.columns(3)
with col1:
    indice_delim = (
        DELIMITADORES_CANDIDATOS.index(delimitador_detectado)
        if delimitador_detectado in DELIMITADORES_CANDIDATOS
        else 0
    )
    delimitador = st.selectbox(
        "Delimitador detectado (ajuste se necessário)",
        DELIMITADORES_CANDIDATOS,
        index=indice_delim,
        format_func=lambda d: ROTULOS_DELIMITADOR.get(d, d),
        key="imp_delimitador",
    )
with col2:
    encoding = st.selectbox(
        "Codificação detectada (ajuste se necessário)",
        ENCODINGS_CANDIDATOS,
        index=ENCODINGS_CANDIDATOS.index(encoding_detectado),
        key="imp_encoding",
    )
with col3:
    tem_cabecalho = st.checkbox(
        "Arquivo possui cabeçalho", value=cabecalho_detectado, key="imp_tem_cabecalho"
    )

if encoding != encoding_detectado:
    try:
        texto_arquivo = conteudo_bytes.decode(encoding)
    except UnicodeDecodeError:
        st.error(f"Não foi possível decodificar o arquivo usando '{encoding}'.")
        st.stop()

try:
    df = pd.read_csv(
        io.StringIO(texto_arquivo),
        sep=delimitador,
        header=0 if tem_cabecalho else None,
        dtype=str,
        keep_default_na=False,
        engine="python",
    )
except Exception:
    st.error(
        "Não foi possível interpretar o arquivo CSV com o delimitador selecionado. "
        "Verifique o arquivo ou ajuste o delimitador acima."
    )
    st.stop()

if not tem_cabecalho:
    df.columns = [f"Coluna {i + 1}" for i in range(len(df.columns))]
df.columns = [str(c) for c in df.columns]

if df.empty:
    st.warning("O arquivo não contém linhas de dados.")
    st.stop()

st.success(f"Arquivo lido com sucesso: {len(df)} linha(s) encontradas.")
st.dataframe(df.head(20), use_container_width=True)

# =======================================================================
# 2. Mapeamento de colunas
# =======================================================================
st.subheader("2. Mapeamento de colunas")
colunas_disponiveis = list(df.columns)

col_a, col_b = st.columns(2)
with col_a:
    col_data = st.selectbox("Coluna de Data", colunas_disponiveis, key="imp_col_data")
    col_valor = st.selectbox("Coluna de Valor", colunas_disponiveis, key="imp_col_valor")
with col_b:
    col_descricao = st.selectbox(
        "Coluna de Descrição", colunas_disponiveis, key="imp_col_descricao"
    )
    col_tipo_opcoes = ["(nenhuma)"] + colunas_disponiveis
    col_tipo_label = st.selectbox(
        "Coluna de Tipo (opcional)", col_tipo_opcoes, key="imp_col_tipo"
    )
    col_tipo = None if col_tipo_label == "(nenhuma)" else col_tipo_label

try:
    contas_ativas = contas.listar_contas(incluir_inativas=False)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

if not contas_ativas:
    st.warning("Cadastre uma conta ativa na página Contas antes de importar um extrato.")
    st.stop()

mapa_contas_imp = {c["id"]: c for c in contas_ativas}
conta_id_importacao = st.selectbox(
    "Conta de destino deste extrato",
    [c["id"] for c in contas_ativas],
    format_func=lambda cid: mapa_contas_imp[cid]["nome"],
    key="imp_conta_id",
)

mapeamento_tipo: dict[str, str | None] = {}
if col_tipo is not None:
    st.markdown("**Mapeamento dos valores da coluna de Tipo**")
    valores_distintos = sorted(
        {str(v).strip() for v in df[col_tipo].tolist() if str(v).strip()}
    )
    if not valores_distintos:
        st.info("A coluna de tipo selecionada não contém valores preenchidos.")
    for valor_bruto_tipo in valores_distintos:
        normalizado = normalizar_texto(valor_bruto_tipo)
        if any(p in normalizado for p in ("receit", "credit", "entrada")):
            padrao = "Receita"
        elif any(p in normalizado for p in ("despes", "debit", "saida", "saída")):
            padrao = "Despesa"
        else:
            padrao = "Não importar (transferência/outro)"
        rotulos_opcao = list(TIPO_MAPEAMENTO_OPCOES.keys())
        escolha = st.selectbox(
            f"Valor '{valor_bruto_tipo}' representa:",
            rotulos_opcao,
            index=rotulos_opcao.index(padrao),
            key=f"imp_tipomap_{hash_arquivo}_{valor_bruto_tipo}",
        )
        mapeamento_tipo[valor_bruto_tipo] = TIPO_MAPEAMENTO_OPCOES[escolha]

# =======================================================================
# 3. Processamento: parsing, tipo, categorização e duplicidade
# =======================================================================
st.subheader("3. Pré-visualização, categorização e duplicidade")

try:
    categorias_todas = categorias_modulo.listar_categorias(incluir_inativas=True)
except ErroBancoDeDados as exc:
    st.error(str(exc))
    st.stop()

mapa_categorias_imp = {c["id"]: c for c in categorias_todas}


def caminho_categoria_imp(categoria_id: int | None) -> str:
    if categoria_id is None:
        return "Sem categoria"
    partes = []
    visitados = set()
    atual = categoria_id
    while atual is not None and atual not in visitados:
        c = mapa_categorias_imp.get(atual)
        if c is None:
            break
        visitados.add(atual)
        partes.append(c["nome"] if c["ativa"] else f"{c['nome']} (inativa)")
        atual = c["categoria_pai_id"]
    return " > ".join(reversed(partes)) if partes else "Sem categoria"


linhas_processadas = []
datas_validas = []

for idx, linha_df in df.iterrows():
    data_bruta = str(linha_df[col_data])
    descricao_bruta = str(linha_df[col_descricao])
    valor_bruto = str(linha_df[col_valor])
    tipo_bruto = str(linha_df[col_tipo]) if col_tipo is not None else None

    linha = importador.processar_linha(
        data_bruta=data_bruta,
        descricao_bruta=descricao_bruta,
        valor_bruto=valor_bruto,
        tipo_bruto=tipo_bruto,
        mapeamento_tipo=mapeamento_tipo if col_tipo is not None else None,
    )
    linha["indice"] = idx
    linhas_processadas.append(linha)
    if linha["data"] is not None:
        datas_validas.append(linha["data"])

# --- detecção de duplicidade (conta + data + tipo + valor + descrição normalizada) ---
if datas_validas:
    try:
        transacoes_existentes = transacoes.listar_transacoes(
            conta_id=conta_id_importacao,
            data_inicial=min(datas_validas),
            data_final=max(datas_validas),
        )
    except ErroBancoDeDados as exc:
        st.error(str(exc))
        transacoes_existentes = []
else:
    transacoes_existentes = []

chaves_existentes = {
    importador.chave_duplicidade(
        conta_id_importacao, t["data_transacao"], t["tipo"], t["valor"], t["descricao"]
    )
    for t in transacoes_existentes
    if t["tipo"] != "transferencia"
}

for linha in linhas_processadas:
    if linha["status"] == "ok":
        chave = importador.chave_duplicidade(
            conta_id_importacao, linha["data"], linha["tipo"], linha["valor"], linha["descricao"]
        )
        if chave in chaves_existentes:
            linha["status"] = "duplicada"
            linha["mensagem"] = "Possível duplicidade"

# --- categorização automática ---
for linha in linhas_processadas:
    if linha["status"] in ("ok", "duplicada"):
        linha["categoria_sugerida_id"] = categorizador.categorizar_descricao(
            linha["descricao"], linha["tipo"]
        )
    else:
        linha["categoria_sugerida_id"] = None

erros_parse = [l for l in linhas_processadas if l["status"] == "erro"]
if erros_parse:
    with st.expander(f"⛔ {len(erros_parse)} linha(s) com erro de leitura"):
        for l in erros_parse:
            st.write(
                f"Linha {l['indice'] + 1}: data='{l['data_bruta']}' "
                f"valor='{l['valor_bruto']}' — {l['mensagem']}"
            )

# --- tabela de revisão ---
larguras_prev = [1, 1, 3, 1, 1, 2, 2]
titulos_prev = ["Importar", "Data", "Descrição", "Tipo", "Valor", "Categoria", "Status"]
for coluna, titulo in zip(st.columns(larguras_prev), titulos_prev):
    coluna.markdown(f"**{titulo}**")

TIPO_LABEL_IMPORT = {"receita": "Receita", "despesa": "Despesa", None: "—"}

for linha in linhas_processadas:
    colunas = st.columns(larguras_prev)
    chave_base = f"{hash_arquivo}_{linha['indice']}"
    pode_selecionar = linha["status"] in ("ok", "duplicada")

    if pode_selecionar:
        chave_sel = f"imp_sel_{chave_base}"
        selecionado = colunas[0].checkbox(
            "", value=(linha["status"] == "ok"), key=chave_sel, label_visibility="collapsed"
        )
    else:
        colunas[0].write("—")
        selecionado = False
    linha["selecionado"] = selecionado

    colunas[1].write(
        linha["data"].strftime("%d/%m/%Y") if linha["data"] else (linha["data_bruta"] or "—")
    )
    colunas[2].write(linha["descricao"] or "—")
    colunas[3].write(TIPO_LABEL_IMPORT.get(linha["tipo"], "—"))
    colunas[4].write(
        formatar_moeda(linha["valor"]) if linha["valor"] is not None else (linha["valor_bruto"] or "—")
    )

    if pode_selecionar:
        ids_compat = sorted(
            (
                c["id"]
                for c in categorias_todas
                if c["ativa"] and (c["tipo"] == "ambos" or c["tipo"] == linha["tipo"])
            ),
            key=caminho_categoria_imp,
        )
        opcoes_cat = [None] + ids_compat
        categoria_default = (
            linha["categoria_sugerida_id"] if linha["categoria_sugerida_id"] in opcoes_cat else None
        )
        categoria_escolhida = colunas[5].selectbox(
            "",
            opcoes_cat,
            index=opcoes_cat.index(categoria_default),
            format_func=caminho_categoria_imp,
            key=f"imp_cat_{chave_base}",
            label_visibility="collapsed",
        )
    else:
        colunas[5].write("—")
        categoria_escolhida = None
    linha["categoria_id"] = categoria_escolhida

    colunas[6].write(f"{STATUS_LABEL.get(linha['status'], '')} {linha['mensagem']}")

# =======================================================================
# 4. Confirmação e importação
# =======================================================================
st.divider()

total_lidas = len(linhas_processadas)
total_erro_parse = sum(1 for l in linhas_processadas if l["status"] == "erro")
total_validas = total_lidas - total_erro_parse
total_duplicadas_info = sum(1 for l in linhas_processadas if l["status"] == "duplicada")
total_revisar = sum(1 for l in linhas_processadas if l["status"] == "revisar")

st.caption(
    f"Linhas lidas: {total_lidas} · Linhas válidas: {total_validas} · "
    f"Possíveis duplicidades: {total_duplicadas_info} · Para revisão: {total_revisar}"
)

if st.button("Importar lançamentos selecionados", type="primary", key="imp_confirmar"):
    importadas = 0
    com_erro = total_erro_parse
    ignoradas = total_revisar
    erros_insercao = []

    for linha in linhas_processadas:
        if linha["status"] not in ("ok", "duplicada"):
            continue
        if not linha["selecionado"]:
            ignoradas += 1
            continue
        try:
            transacoes.criar_transacao(
                tipo=linha["tipo"],
                descricao=linha["descricao"],
                valor=linha["valor"],
                data_transacao=linha["data"],
                conta_id=conta_id_importacao,
                categoria_id=linha["categoria_id"],
                origem="importacao",
            )
            importadas += 1
        except (ValueError, ErroBancoDeDados) as exc:
            com_erro += 1
            erros_insercao.append((linha["indice"], linha["descricao"], str(exc)))
        except Exception:
            com_erro += 1
            erros_insercao.append(
                (linha["indice"], linha["descricao"], "Erro inesperado ao salvar esta linha.")
            )

    st.success("Importação concluída.")
    st.markdown(
        f"""
- **Linhas lidas:** {total_lidas}
- **Linhas válidas:** {total_validas}
- **Importadas:** {importadas}
- **Ignoradas:** {ignoradas}
- **Duplicadas (detectadas):** {total_duplicadas_info}
- **Com erro:** {com_erro}
"""
    )
    if erros_insercao:
        with st.expander(f"Ver {len(erros_insercao)} linha(s) com erro ao salvar"):
            for idx_linha, descricao_linha, motivo in erros_insercao:
                st.write(f"Linha {idx_linha + 1}: {descricao_linha} — {motivo}")
