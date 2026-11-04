from fastapi import APIRouter, Depends

from app.core.security import obter_usuario_atual
from app.schemas.simulador import AporteNecessarioEntrada, ProjecaoEntrada, TempoMetaEntrada
from src import simulador

router = APIRouter(prefix="/simulador", tags=["Simulador"])

# Funções puras (sem banco) — exigem apenas um usuário autenticado válido,
# sem precisar do contexto de RLS (não consultam dado nenhum).


@router.post("/tempo-meta")
def tempo_meta(dados: TempoMetaEntrada, usuario_id: str = Depends(obter_usuario_atual)):
    return simulador.calcular_meses_para_meta(
        dados.valor_atual, dados.valor_alvo, dados.aporte_mensal
    )


@router.post("/aporte-necessario")
def aporte_necessario(dados: AporteNecessarioEntrada, usuario_id: str = Depends(obter_usuario_atual)):
    return simulador.calcular_aporte_necessario(dados.valor_atual, dados.valor_alvo, dados.meses)


@router.post("/projecao")
def projecao(dados: ProjecaoEntrada, usuario_id: str = Depends(obter_usuario_atual)):
    return simulador.projetar_saldo(dados.saldo_inicial, dados.aporte_mensal, dados.meses)
