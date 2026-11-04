from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.categorias import CategoriaAtualizar, CategoriaCriar
from src import categorias

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("")
@com_usuario
def listar(
    tipo: str | None = None,
    incluir_inativas: bool = False,
    usuario_id: str = Depends(obter_usuario_atual),
):
    return categorias.listar_categorias(tipo=tipo, incluir_inativas=incluir_inativas)


@router.post("", status_code=201)
@com_usuario
def criar(dados: CategoriaCriar, usuario_id: str = Depends(obter_usuario_atual)):
    categoria_id = categorias.criar_categoria(**dados.model_dump())
    invalidar_usuario(usuario_id)
    return categorias.obter_categoria(categoria_id)


@router.get("/{categoria_id}")
@com_usuario
def obter(categoria_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    categoria = categorias.obter_categoria(categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    return categoria


@router.patch("/{categoria_id}")
@com_usuario
def atualizar(
    categoria_id: int, dados: CategoriaAtualizar, usuario_id: str = Depends(obter_usuario_atual)
):
    campos = dados.model_dump(exclude_unset=True)
    categorias.atualizar_categoria(categoria_id, **campos)
    invalidar_usuario(usuario_id)
    categoria = categorias.obter_categoria(categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    return categoria


@router.delete("/{categoria_id}", status_code=204)
@com_usuario
def excluir(categoria_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    categorias.excluir_categoria(categoria_id)
    invalidar_usuario(usuario_id)
