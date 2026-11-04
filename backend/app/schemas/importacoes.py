from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class LinhaImportacao(BaseModel):
    indice: int
    data: date | None
    data_bruta: str
    descricao: str
    valor: Decimal | None
    valor_bruto: str
    tipo: str | None
    status: str
    mensagem: str
    possivel_transferencia: bool
    possivel_pagamento_fatura: bool
    categoria_sugerida_id: int | None = None


class PreviaImportacao(BaseModel):
    colunas_disponiveis: list[str] | None = None
    delimitador_detectado: str | None = None
    encoding_detectado: str | None = None
    cabecalho_detectado: bool | None = None
    linhas: list[dict] | None = None
    total_lidas: int | None = None


class LinhaConfirmar(BaseModel):
    indice: int
    classificacao: str = "normal"
    tipo: str
    descricao: str
    valor: Decimal
    data_transacao: date
    categoria_id: int | None = None
    outra_conta_id: int | None = None
    cartao_vinculado_id: int | None = None


class ConfirmarImportacao(BaseModel):
    conta_id_importacao: int
    linhas: list[LinhaConfirmar]
