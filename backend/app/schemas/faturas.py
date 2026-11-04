from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PagamentoFaturaCriar(BaseModel):
    conta_id: int
    valor: Decimal
    data_pagamento: date
