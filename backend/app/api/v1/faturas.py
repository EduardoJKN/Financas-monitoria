from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import invalidar_usuario
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from app.schemas.faturas import PagamentoFaturaCriar
from src import faturas

router = APIRouter(prefix="/faturas", tags=["Faturas"])


def _com_totais(fatura: dict) -> dict:
    total = faturas.calcular_total_fatura(fatura["id"])
    total_pago = faturas.calcular_total_pago(fatura["id"])
    return {
        **fatura,
        "total": total,
        "total_pago": total_pago,
        "saldo_devedor": total - total_pago,
        "status_exibicao": faturas.status_exibicao_fatura(fatura, hoje=date.today()),
    }


@router.get("")
@com_usuario
def listar(cartao_id: int | None = None, usuario_id: str = Depends(obter_usuario_atual)):
    return [_com_totais(f) for f in faturas.listar_faturas(cartao_id=cartao_id)]


@router.get("/{fatura_id}")
@com_usuario
def obter(fatura_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    fatura = faturas.obter_fatura(fatura_id)
    if fatura is None:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")
    return _com_totais(fatura)


@router.get("/{fatura_id}/pagamentos")
@com_usuario
def listar_pagamentos(fatura_id: int, usuario_id: str = Depends(obter_usuario_atual)):
    return faturas.listar_pagamentos(fatura_id)


@router.post("/{fatura_id}/pagamentos", status_code=201)
@com_usuario
def pagar(fatura_id: int, dados: PagamentoFaturaCriar, usuario_id: str = Depends(obter_usuario_atual)):
    pagamento_id = faturas.registrar_pagamento_fatura(
        fatura_id, dados.conta_id, dados.valor, dados.data_pagamento
    )
    invalidar_usuario(usuario_id)
    fatura = faturas.obter_fatura(fatura_id)
    return {"pagamento_id": pagamento_id, "fatura": _com_totais(fatura)}
