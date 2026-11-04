from fastapi import APIRouter

from app.api.v1 import (
    cartoes,
    categorias,
    compromissos,
    contas,
    dashboard,
    faturas,
    importacoes,
    metas,
    recorrencias,
    regras,
    simulador,
    transacoes,
)

router_v1 = APIRouter(prefix="/api/v1")
router_v1.include_router(contas.router)
router_v1.include_router(categorias.router)
router_v1.include_router(regras.router)
router_v1.include_router(transacoes.router)
router_v1.include_router(recorrencias.router)
router_v1.include_router(cartoes.router)
router_v1.include_router(faturas.router)
router_v1.include_router(importacoes.router)
router_v1.include_router(metas.router)
router_v1.include_router(simulador.router)
router_v1.include_router(dashboard.router)
router_v1.include_router(compromissos.router)
