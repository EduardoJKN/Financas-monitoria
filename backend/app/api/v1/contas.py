from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.contas import ConciliarConta, ContaAtualizar, ContaCriar
from src import contas, resumo_financeiro as resumo

router = APIRouter(prefix="/contas", tags=["Contas"])


@router.get("")
@com_usuario
def listar(incluir_inativas: bool = False, usuario_id: str = Depends(obter_usuario_atual)):
    return contas.listar_contas(incluir_inativas=incluir_inativas)


@router.post("", status_code=201)
@com_usuario
def criar(dados: ContaCriar, usuario_id: str = Depends(obter_usuario_atual)):
    conta_id = contas.criar_conta(**dados.model_dump())
    invalidar_usuario(usuario_id)
    return contas.obter_conta(conta_id)


@router.get("/{conta_id}")
@com_usuario
def obter(conta_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    conta = contas.obter_conta(conta_id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return conta


@router.patch("/{conta_id}")
@com_usuario
def atualizar(conta_id: int, dados: ContaAtualizar, usuario_id: str = Depends(obter_usuario_atual)):
    campos = dados.model_dump(exclude_unset=True)
    contas.atualizar_conta(conta_id, **campos)
    invalidar_usuario(usuario_id)
    conta = contas.obter_conta(conta_id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return conta


@router.delete("/{conta_id}", status_code=204)
@com_usuario
def excluir(conta_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    contas.excluir_conta(conta_id)
    invalidar_usuario(usuario_id)


@router.post("/{conta_id}/conciliar")
@com_usuario
def conciliar(conta_id: int, dados: ConciliarConta, usuario_id: str = Depends(obter_usuario_atual)):
    resultado = resumo.conciliar_conta(conta_id, dados.data_referencia, dados.saldo_informado)
    invalidar_usuario(usuario_id)
    return resultado


@router.get("/{conta_id}/conciliar/pre-visualizar")
@com_usuario
def pre_visualizar_conciliacao(
    conta_id: int,
    data_referencia: str,
    saldo_informado: str,
    usuario_id: str = Depends(obter_usuario_atual),
):
    from datetime import date
    from decimal import Decimal

    return resumo.pre_visualizar_conciliacao(
        conta_id, date.fromisoformat(data_referencia), Decimal(saldo_informado)
    )
