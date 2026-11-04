"""Importação de extratos (CSV/OFX).

Todos os endpoints são síncronos (`def`, não `async def`) de propósito —
o decorator `com_usuario` (ver app/core/contexto_usuario.py) só garante a
propagação segura do contexto de RLS para funções síncronas, e todo o
pipeline reaproveitado de `src/` (pandas, SQLAlchemy) já é síncrono.
`UploadFile.file` é o objeto de arquivo síncrono equivalente a
`await arquivo.read()`.

REVALIDAÇÃO: a confirmação (`POST /importacoes/confirmar`) nunca confia em
"classificação"/"categoria sugerida" computada pelo frontend como verdade
absoluta — cada linha é recriada do zero chamando
`importacao_execucao.confirmar_linha`, que por sua vez chama
`transacoes.criar_transacao`/`faturas.registrar_pagamento_fatura` — as
MESMAS funções que validam conta ativa, categoria compatível, forma de
pagamento, etc. Um valor ou data adulterados pelo cliente são validados
exatamente como seriam num lançamento manual.
"""

import io
import json

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.importacoes import ConfirmarImportacao
from src import categorizador, importacao_execucao, importador
from src import ofx as ofx_modulo
from src import resumo_financeiro as resumo
from src import transacoes
from src.banco_de_dados import ErroBancoDeDados

router = APIRouter(prefix="/importacoes", tags=["Importação"])

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024


def _ler_arquivo(arquivo: UploadFile) -> bytes:
    conteudo = arquivo.file.read()
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 10 MB.")
    if not conteudo or not conteudo.strip():
        raise HTTPException(status_code=422, detail="O arquivo está vazio.")
    return conteudo


def _detectar_duplicidade_e_categoria(linhas_processadas: list[dict], conta_id_importacao: int) -> list[dict]:
    """Mesma lógica já usada pela prévia no Streamlit (duplicidade por
    conta+data+tipo+valor+descrição normalizada, e sugestão de categoria
    via categorizador.categorizar_descricao) — reaproveitada, não
    recriada."""
    datas_validas = [l["data"] for l in linhas_processadas if l["data"] is not None]
    existentes = []
    if datas_validas:
        try:
            existentes = transacoes.listar_transacoes(
                conta_id=conta_id_importacao,
                data_inicial=min(datas_validas),
                data_final=max(datas_validas),
                limit=10000,
            )
        except ErroBancoDeDados:
            existentes = []

    chaves_existentes = {
        importador.chave_duplicidade(
            conta_id_importacao, t["data_transacao"], t["tipo"], t["valor"], t["descricao"]
        )
        for t in existentes
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

        if linha["status"] in ("ok", "duplicada"):
            linha["categoria_sugerida_id"] = categorizador.categorizar_descricao(
                linha["descricao"], linha["tipo"]
            )
        else:
            linha["categoria_sugerida_id"] = None

    return linhas_processadas


@router.post("/csv/previsualizar")
@com_usuario
def previsualizar_csv(
    conta_id_importacao: int = Form(...),
    delimitador: str | None = Form(None),
    encoding: str | None = Form(None),
    tem_cabecalho: bool | None = Form(None),
    col_data: str | None = Form(None),
    col_valor: str | None = Form(None),
    col_descricao: str | None = Form(None),
    col_tipo: str | None = Form(None),
    mapeamento_tipo: str | None = Form(None),
    arquivo: UploadFile = File(...),
    usuario_id: str = Depends(obter_usuario_atual),
):
    conteudo = _ler_arquivo(arquivo)

    encoding_final = encoding or importador.detectar_encoding(conteudo)
    if encoding_final is None:
        raise HTTPException(422, "Não foi possível identificar a codificação do arquivo.")
    try:
        texto = conteudo.decode(encoding_final)
    except UnicodeDecodeError:
        raise HTTPException(422, f"Não foi possível decodificar o arquivo usando '{encoding_final}'.")
    if not texto.strip():
        raise HTTPException(422, "O arquivo está vazio.")

    delimitador_final = delimitador or importador.detectar_delimitador(texto) or ","
    cabecalho_final = (
        tem_cabecalho if tem_cabecalho is not None else importador.detectar_cabecalho(texto)
    )

    try:
        df = pd.read_csv(
            io.StringIO(texto),
            sep=delimitador_final,
            header=0 if cabecalho_final else None,
            dtype=str,
            keep_default_na=False,
            engine="python",
        )
    except Exception:
        raise HTTPException(
            422, "Não foi possível interpretar o CSV com o delimitador informado."
        )

    if not cabecalho_final:
        df.columns = [f"Coluna {i + 1}" for i in range(len(df.columns))]
    df.columns = [str(c) for c in df.columns]

    if df.empty:
        raise HTTPException(422, "O arquivo não contém linhas de dados.")

    # Fase 1 (sem col_data/col_valor/col_descricao ainda): devolve os
    # metadados para o frontend montar a UI de mapeamento de colunas.
    if not (col_data and col_valor and col_descricao):
        return {
            "fase": "mapeamento_necessario",
            "colunas_disponiveis": list(df.columns),
            "delimitador_detectado": delimitador_final,
            "encoding_detectado": encoding_final,
            "cabecalho_detectado": cabecalho_final,
            "total_linhas": len(df),
            "amostra": df.head(10).to_dict(orient="records"),
        }

    mapeamento_dict = json.loads(mapeamento_tipo) if mapeamento_tipo else None

    linhas_processadas = []
    for idx, linha_df in df.iterrows():
        linha = importador.processar_linha(
            data_bruta=str(linha_df[col_data]),
            descricao_bruta=str(linha_df[col_descricao]),
            valor_bruto=str(linha_df[col_valor]),
            tipo_bruto=str(linha_df[col_tipo]) if col_tipo else None,
            mapeamento_tipo=mapeamento_dict,
        )
        linha["indice"] = idx
        linhas_processadas.append(linha)

    linhas_processadas = _detectar_duplicidade_e_categoria(linhas_processadas, conta_id_importacao)
    return {
        "fase": "pre_visualizacao",
        "linhas": linhas_processadas,
        "total_lidas": len(linhas_processadas),
    }


@router.post("/ofx/previsualizar")
@com_usuario
def previsualizar_ofx(
    conta_id_importacao: int = Form(...),
    arquivo: UploadFile = File(...),
    usuario_id: str = Depends(obter_usuario_atual),
):
    conteudo = _ler_arquivo(arquivo)
    try:
        linhas_processadas = ofx_modulo.ler_transacoes_ofx(conteudo)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    linhas_processadas = _detectar_duplicidade_e_categoria(linhas_processadas, conta_id_importacao)

    saldo_info = None
    saldo_ofx = ofx_modulo.ler_saldo_ofx(conteudo)
    if saldo_ofx is not None:
        try:
            saldo_app = resumo.calcular_saldo_conta(
                conta_id_importacao, ate_data=saldo_ofx["data_saldo"]
            )
            saldo_info = {
                "saldo_banco": saldo_ofx["saldo_banco"],
                "data_saldo": saldo_ofx["data_saldo"],
                "saldo_aplicativo": saldo_app,
                "diferenca": saldo_ofx["saldo_banco"] - saldo_app,
            }
        except ErroBancoDeDados:
            saldo_info = None

    return {
        "fase": "pre_visualizacao",
        "linhas": linhas_processadas,
        "total_lidas": len(linhas_processadas),
        "saldo": saldo_info,
    }


@router.post("/confirmar")
@com_usuario
def confirmar(dados: ConfirmarImportacao, usuario_id: str = Depends(obter_usuario_atual)):
    importadas = 0
    com_erro: list[dict] = []
    for linha in dados.linhas:
        try:
            importacao_execucao.confirmar_linha(
                classificacao=linha.classificacao,
                tipo=linha.tipo,
                descricao=linha.descricao,
                valor=linha.valor,
                data_transacao=linha.data_transacao,
                conta_id_importacao=dados.conta_id_importacao,
                categoria_id=linha.categoria_id,
                outra_conta_id=linha.outra_conta_id,
                cartao_vinculado_id=linha.cartao_vinculado_id,
            )
            importadas += 1
        except (ValueError, ErroBancoDeDados) as exc:
            com_erro.append(
                {"indice": linha.indice, "descricao": linha.descricao, "motivo": str(exc)}
            )

    invalidar_usuario(usuario_id)
    return {"importadas": importadas, "total": len(dados.linhas), "com_erro": com_erro}
