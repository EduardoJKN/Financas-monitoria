from fastapi import APIRouter, Depends, HTTPException

from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.metas import MetaAtualizar, MetaCriar
from src import metas

router = APIRouter(prefix="/metas", tags=["Metas"])


def _com_progresso(meta: dict) -> dict:
    return {**meta, "progresso": metas.calcular_progresso_meta(meta["id"])}


@router.get("")
@com_usuario
def listar(apenas_em_andamento: bool = False, usuario_id: str = Depends(obter_usuario_atual)):
    return [_com_progresso(m) for m in metas.listar_metas(apenas_em_andamento=apenas_em_andamento)]


@router.post("", status_code=201)
@com_usuario
def criar(dados: MetaCriar, usuario_id: str = Depends(obter_usuario_atual)):
    meta_id = metas.criar_meta(**dados.model_dump())
    return _com_progresso(metas.obter_meta(meta_id))


@router.get("/{meta_id}")
@com_usuario
def obter(meta_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    meta = metas.obter_meta(meta_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    return _com_progresso(meta)


@router.patch("/{meta_id}")
@com_usuario
def atualizar(meta_id: int, dados: MetaAtualizar, usuario_id: str = Depends(obter_usuario_atual)):
    campos = dados.model_dump(exclude_unset=True)
    metas.atualizar_meta(meta_id, **campos)
    meta = metas.obter_meta(meta_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    return _com_progresso(meta)


@router.delete("/{meta_id}", status_code=204)
@com_usuario
def excluir(meta_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    metas.excluir_meta(meta_id)
