from decimal import Decimal

from pydantic import BaseModel


class CartaoCriar(BaseModel):
    nome: str
    limite: Decimal
    dia_fechamento: int
    dia_vencimento: int
    instituicao: str | None = None
    conta_pagamento_id: int | None = None


class CartaoAtualizar(BaseModel):
    nome: str | None = None
    instituicao: str | None = None
    limite: Decimal | None = None
    dia_fechamento: int | None = None
    dia_vencimento: int | None = None
    conta_pagamento_id: int | None = None
    ativo: bool | None = None
