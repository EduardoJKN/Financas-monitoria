from decimal import Decimal

from pydantic import BaseModel


class TempoMetaEntrada(BaseModel):
    valor_atual: Decimal
    valor_alvo: Decimal
    aporte_mensal: Decimal


class AporteNecessarioEntrada(BaseModel):
    valor_atual: Decimal
    valor_alvo: Decimal
    meses: int


class ProjecaoEntrada(BaseModel):
    saldo_inicial: Decimal
    aporte_mensal: Decimal
    meses: int
