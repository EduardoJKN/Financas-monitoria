from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.transacoes import (
    LIMITE_MAXIMO,
    LIMITE_PADRAO,
    ParcelamentoCriar,
    ParcelamentoPreVisualizar,
    TransacaoAtualizar,
    TransacaoCriar,
)
from src import transacoes

router = APIRouter(prefix="/transacoes", tags=["Lançamentos"])


@router.get("")
@com_usuario
def listar(
    tipo: str | None = None,
    conta_id: int | None = None,
    categoria_id: int | None = None,
    origem: str | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
    texto_busca: str | None = None,
    limit: int = LIMITE_PADRAO,
    offset: int = 0,
    usuario_id: str = Depends(obter_usuario_atual),
):
    limit = min(max(limit, 1), LIMITE_MAXIMO)
    offset = max(offset, 0)
    return transacoes.listar_transacoes(
        tipo=tipo,
        conta_id=conta_id,
        categoria_id=categoria_id,
        origem=origem,
        data_inicial=data_inicial,
        data_final=data_final,
        texto_busca=texto_busca,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=201)
@com_usuario
def criar(dados: TransacaoCriar, usuario_id: str = Depends(obter_usuario_atual)):
    transacao_id = transacoes.criar_transacao(**dados.model_dump())
    invalidar_usuario(usuario_id)
    return transacoes.obter_transacao(transacao_id)


@router.get("/{transacao_id}")
@com_usuario
def obter(transacao_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    transacao = transacoes.obter_transacao(transacao_id)
    if transacao is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return transacao


@router.patch("/{transacao_id}")
@com_usuario
def atualizar(
    transacao_id: int, dados: TransacaoAtualizar, usuario_id: str = Depends(obter_usuario_atual)
):
    campos = dados.model_dump(exclude_unset=True)
    transacoes.atualizar_transacao(transacao_id, **campos)
    invalidar_usuario(usuario_id)
    transacao = transacoes.obter_transacao(transacao_id)
    if transacao is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return transacao


@router.delete("/{transacao_id}", status_code=204)
@com_usuario
def excluir(transacao_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    transacoes.excluir_transacao(transacao_id)
    invalidar_usuario(usuario_id)


@router.post("/parcelamento/pre-visualizar")
@com_usuario
def pre_visualizar_parcelamento(
    dados: ParcelamentoPreVisualizar, usuario_id: str = Depends(obter_usuario_atual)
):
    """Pré-visualiza as parcelas (divisão exata em centavos), sem tocar o
    banco."""
    parcelas = transacoes.simular_parcelas(
        dados.valor_total, dados.data_primeira_parcela, dados.total_parcelas
    )
    return [
        {"numero_parcela": p["numero_parcela"], "data": p["data"], "valor": p["valor"]}
        for p in parcelas
    ]


@router.post("/parcelamento", status_code=201)
@com_usuario
def criar_parcelamento(dados: ParcelamentoCriar, usuario_id: str = Depends(obter_usuario_atual)):
    ids = transacoes.criar_transacao_parcelada(**dados.model_dump())
    invalidar_usuario(usuario_id)
    return {"transacao_ids": ids}
