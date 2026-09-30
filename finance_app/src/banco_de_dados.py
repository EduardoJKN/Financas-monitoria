import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def obter_url_banco_de_dados() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL não definida. Copie .env.example para .env e configure a conexão."
        )
    return url


@lru_cache(maxsize=1)
def obter_engine() -> Engine:
    return create_engine(obter_url_banco_de_dados(), pool_pre_ping=True)


def testar_conexao() -> bool:
    try:
        with obter_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
