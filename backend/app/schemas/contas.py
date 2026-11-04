from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

TIPOS_CONTA = (
    "conta_corrente",
    "conta_digital",
    "poupanca",
    "dinheiro",
    "investimento",
    "outro",
)


class ContaCriar(BaseModel):
    nome: str
    tipo: str
    instituicao: str | None = None
    saldo_inicial: Decimal = Decimal("0")
    data_saldo_inicial: date | None = None


class ContaAtualizar(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    instituicao: str | None = None
    saldo_inicial: Decimal | None = None
    data_saldo_inicial: date | None = None
    ativa: bool | None = None


class ContaSaida(BaseModel):
    id: int
    nome: str
    tipo: str
    instituicao: str | None
    saldo_inicial: Decimal
    data_saldo_inicial: date | None
    ativa: bool


class ConciliarConta(BaseModel):
    data_referencia: date
    saldo_informado: Decimal


class PreVisualizarConciliacao(BaseModel):
    conta_id: int
    data_referencia: date
    saldo_calculado_atual: Decimal
    saldo_informado: Decimal
    diferenca: Decimal
