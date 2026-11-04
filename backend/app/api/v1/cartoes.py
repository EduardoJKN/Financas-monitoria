from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from src import cartoes, faturas
from src.banco_de_dados import ErroBancoDeDados

from app.schemas.cartoes import CartaoAtualizar, CartaoCriar

router = APIRouter(prefix="/cartoes", tags=["Cartões"])


def _com_limites(cartao: dict) -> dict:
    try:
        limite_utilizado = faturas.calcular_limite_utilizado(cartao["id"])
    except ErroBancoDeDados:
        limite_utilizado = None
    limite_disponivel = (
        cartao["limite"] - limite_utilizado if limite_utilizado is not None else None
    )
    hoje = date.today()
    proxima_fatura = None
    for f in faturas.listar_faturas(cartao_id=cartao["id"]):
        mes_ref_atual = faturas.calcular_mes_referencia(cartao["dia_fechamento"], hoje)
        if f["mes_referencia"] == mes_ref_atual:
            proxima_fatura = f
            break
    return {
        **cartao,
        "limite_utilizado": limite_utilizado,
        "limite_disponivel": limite_disponivel,
        "fatura_atual": proxima_fatura,
    }


@router.get("")
@com_usuario
def listar(incluir_inativos: bool = False, usuario_id: str = Depends(obter_usuario_atual)):
    return [_com_limites(c) for c in cartoes.listar_cartoes(incluir_inativos=incluir_inativos)]


@router.post("", status_code=201)
@com_usuario
def criar(dados: CartaoCriar, usuario_id: str = Depends(obter_usuario_atual)):
    cartao_id = cartoes.criar_cartao(**dados.model_dump())
    invalidar_usuario(usuario_id)
    return _com_limites(cartoes.obter_cartao(cartao_id))


@router.get("/{cartao_id}")
@com_usuario
def obter(cartao_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    cartao = cartoes.obter_cartao(cartao_id)
    if cartao is None:
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")
    return _com_limites(cartao)


@router.patch("/{cartao_id}")
@com_usuario
def atualizar(cartao_id: int, dados: CartaoAtualizar, usuario_id: str = Depends(obter_usuario_atual)):
    campos = dados.model_dump(exclude_unset=True)
    cartoes.atualizar_cartao(cartao_id, **campos)
    invalidar_usuario(usuario_id)
    cartao = cartoes.obter_cartao(cartao_id)
    if cartao is None:
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")
    return _com_limites(cartao)


@router.delete("/{cartao_id}", status_code=204)
@com_usuario
def excluir(cartao_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    cartoes.excluir_cartao(cartao_id)
    invalidar_usuario(usuario_id)
