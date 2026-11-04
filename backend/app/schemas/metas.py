from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MetaCriar(BaseModel):
    nome: str
    data_inicio: date
    valor_alvo: Decimal
    valor_atual: Decimal = Decimal("0")
    descricao: str | None = None
    data_limite: date | None = None


class MetaAtualizar(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    valor_alvo: Decimal | None = None
    valor_atual: Decimal | None = None
    data_inicio: date | None = None
    data_limite: date | None = None
