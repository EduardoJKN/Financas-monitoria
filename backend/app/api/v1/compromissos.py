from fastapi import APIRouter, Depends

from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from src import compromissos_futuros

router = APIRouter(prefix="/compromissos", tags=["Compromissos futuros"])


@router.get("/previstos")
@com_usuario
def previstos(meses: int = 4, usuario_id: str = Depends(obter_usuario_atual)):
    meses = min(max(meses, 1), 12)
    return {"compromissos": compromissos_futuros.compromissos_previstos(meses=meses)}
