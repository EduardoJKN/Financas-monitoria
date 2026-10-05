import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


class ErroBancoDeDados(Exception):
    """Erro genérico da camada de acesso a dados.

    Usada para encapsular falhas do driver/SQLAlchemy sem propagar a
    mensagem original (que pode conter detalhes de conexão) para quem
    chama a camada de acesso a dados.
    """


def obter_url_banco_de_dados() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL não definida. Copie .env.example para .env e configure a conexão."
        )
    if url.startswith("postgresql://"):
        # Força o driver psycopg2 (instalado via requirements.txt) em vez de
        # depender da resolução implícita de driver do SQLAlchemy, que pode
        # variar entre versões.
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
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
