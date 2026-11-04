from pydantic import BaseModel


class RegraCriar(BaseModel):
    texto_busca: str
    operador: str
    categoria_id: int
    prioridade: int = 0


class RegraAtualizar(BaseModel):
    texto_busca: str | None = None
    operador: str | None = None
    categoria_id: int | None = None
    prioridade: int | None = None
    ativa: bool | None = None


class AplicarRegra(BaseModel):
    transacao_ids: list[int] | None = None
    somente_sem_categoria: bool = True


class AplicarTodasRegras(BaseModel):
    transacao_ids: list[int]
