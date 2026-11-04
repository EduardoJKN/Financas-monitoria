import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200


class TransacaoCriar(BaseModel):
    tipo: str
    descricao: str
    valor: Decimal
    data_transacao: date
    conta_id: int | None = None
    cartao_id: int | None = None
    conta_destino_id: int | None = None
    categoria_id: int | None = None
    origem: str = "manual"
    observacao: str | None = None
    grupo_parcelamento: uuid.UUID | None = None
    numero_parcela: int | None = None
    total_parcelas: int | None = None


class TransacaoAtualizar(BaseModel):
    tipo: str | None = None
    descricao: str | None = None
    valor: Decimal | None = None
    data_transacao: date | None = None
    conta_id: int | None = None
    cartao_id: int | None = None
    conta_destino_id: int | None = None
    categoria_id: int | None = None
    origem: str | None = None
    observacao: str | None = None
    grupo_parcelamento: uuid.UUID | None = None
    numero_parcela: int | None = None
    total_parcelas: int | None = None


class ParcelamentoPreVisualizar(BaseModel):
    valor_total: Decimal
    data_primeira_parcela: date
    total_parcelas: int


class ParcelamentoCriar(BaseModel):
    tipo: str
    descricao: str
    valor_total: Decimal
    data_primeira_parcela: date
    total_parcelas: int
    conta_id: int | None = None
    cartao_id: int | None = None
    categoria_id: int | None = None
    observacao: str | None = None
    origem: str = "manual"
