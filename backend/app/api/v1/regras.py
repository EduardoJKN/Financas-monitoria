from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.regras import AplicarRegra, AplicarTodasRegras, RegraAtualizar, RegraCriar
from src import categorizador

router = APIRouter(prefix="/regras", tags=["Regras de categorização"])


@router.get("")
@com_usuario
def listar(
    categoria_id: int | None = None,
    incluir_inativas: bool = False,
    usuario_id: str = Depends(obter_usuario_atual),
):
    return categorizador.listar_regras(categoria_id=categoria_id, incluir_inativas=incluir_inativas)


@router.post("", status_code=201)
@com_usuario
def criar(dados: RegraCriar, usuario_id: str = Depends(obter_usuario_atual)):
    regra_id = categorizador.criar_regra(**dados.model_dump())
    return categorizador.obter_regra(regra_id)


@router.get("/{regra_id}")
@com_usuario
def obter(regra_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    regra = categorizador.obter_regra(regra_id)
    if regra is None:
        raise HTTPException(status_code=404, detail="Regra não encontrada.")
    return regra


@router.patch("/{regra_id}")
@com_usuario
def atualizar(regra_id: int, dados: RegraAtualizar, usuario_id: str = Depends(obter_usuario_atual)):
    campos = dados.model_dump(exclude_unset=True)
    categorizador.atualizar_regra(regra_id, **campos)
    regra = categorizador.obter_regra(regra_id)
    if regra is None:
        raise HTTPException(status_code=404, detail="Regra não encontrada.")
    return regra


@router.delete("/{regra_id}", status_code=204)
@com_usuario
def excluir(regra_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    categorizador.excluir_regra(regra_id)


@router.get("/{regra_id}/pre-visualizar")
@com_usuario
def pre_visualizar(
    regra_id: int, somente_sem_categoria: bool = True, usuario_id: str = Depends(obter_usuario_atual)
):
    """Lançamentos já existentes que esta regra passaria a categorizar."""
    return categorizador.buscar_transacoes_compativeis_regra(regra_id, somente_sem_categoria)


@router.post("/{regra_id}/aplicar")
@com_usuario
def aplicar(regra_id: int, dados: AplicarRegra, usuario_id: str = Depends(obter_usuario_atual)):
    total = categorizador.aplicar_regra_em_transacoes_existentes(
        regra_id, dados.transacao_ids, dados.somente_sem_categoria
    )
    invalidar_usuario(usuario_id)
    return {"total_aplicado": total}


@router.get("/aplicar-todas/pre-visualizar")
@com_usuario
def pre_visualizar_todas(usuario_id: str = Depends(obter_usuario_atual)):
    """Para cada lançamento sem categoria, a categoria que seria sugerida
    por todas as regras ativas (sem alterar nada)."""
    return categorizador.prever_aplicacao_todas_regras()


@router.post("/aplicar-todas")
@com_usuario
def aplicar_todas(dados: AplicarTodasRegras, usuario_id: str = Depends(obter_usuario_atual)):
    total = categorizador.aplicar_todas_regras_em_transacoes_sem_categoria(dados.transacao_ids)
    invalidar_usuario(usuario_id)
    return {"total_aplicado": total}
