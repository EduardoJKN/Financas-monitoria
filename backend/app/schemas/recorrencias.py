from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RecorrenciaCriar(BaseModel):
    tipo: str
    descricao: str
    valor: Decimal
    conta_id: int
    periodicidade: str
    data_inicio: date
    categoria_id: int | None = None
    observacao: str | None = None
    data_fim: date | None = None


class RecorrenciaAtualizar(BaseModel):
    tipo: str | None = None
    descricao: str | None = None
    valor: Decimal | None = None
    conta_id: int | None = None
    categoria_id: int | None = None
    periodicidade: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    ativa: bool | None = None


class GerarPendentes(BaseModel):
    hoje: date | None = None
