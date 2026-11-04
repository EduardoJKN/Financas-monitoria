from pydantic import BaseModel


class CategoriaCriar(BaseModel):
    nome: str
    tipo: str
    categoria_pai_id: int | None = None


class CategoriaAtualizar(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    categoria_pai_id: int | None = None
    ativa: bool | None = None
