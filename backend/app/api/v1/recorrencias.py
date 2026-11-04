from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.recorrencias import GerarPendentes, RecorrenciaAtualizar, RecorrenciaCriar
from src import recorrencias

router = APIRouter(prefix="/recorrencias", tags=["Recorrências"])


@router.get("")
@com_usuario
def listar(incluir_inativas: bool = False, usuario_id: str = Depends(obter_usuario_atual)):
    return recorrencias.listar_recorrencias(incluir_inativas=incluir_inativas)


@router.post("", status_code=201)
@com_usuario
def criar(dados: RecorrenciaCriar, usuario_id: str = Depends(obter_usuario_atual)):
    recorrencia_id = recorrencias.criar_recorrencia(**dados.model_dump())
    return recorrencias.obter_recorrencia(recorrencia_id)


@router.get("/{recorrencia_id}")
@com_usuario
def obter(recorrencia_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    recorrencia = recorrencias.obter_recorrencia(recorrencia_id)
    if recorrencia is None:
        raise HTTPException(status_code=404, detail="Recorrência não encontrada.")
    return recorrencia


@router.patch("/{recorrencia_id}")
@com_usuario
def atualizar(
    recorrencia_id: int, dados: RecorrenciaAtualizar, usuario_id: str = Depends(obter_usuario_atual)
):
    campos = dados.model_dump(exclude_unset=True)
    recorrencias.atualizar_recorrencia(recorrencia_id, **campos)
    recorrencia = recorrencias.obter_recorrencia(recorrencia_id)
    if recorrencia is None:
        raise HTTPException(status_code=404, detail="Recorrência não encontrada.")
    return recorrencia


@router.delete("/{recorrencia_id}", status_code=204)
@com_usuario
def excluir(recorrencia_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    recorrencias.excluir_recorrencia(recorrencia_id)


@router.post("/gerar-pendentes")
@com_usuario
def gerar_pendentes(dados: GerarPendentes, usuario_id: str = Depends(obter_usuario_atual)):
    resultado = recorrencias.gerar_lancamentos_pendentes(dados.hoje)
    invalidar_usuario(usuario_id)
    return resultado
