"""Configuração do backend via variáveis de ambiente.

O backend só precisa da conexão restrita (APP_DATABASE_URL, role
app_runtime) para servir dados de usuários autenticados, e de SUPABASE_URL
para buscar o JWKS público do projeto (validação local de JWT — ver
app/core/security.py). NÃO exige DATABASE_URL (role administrativa) nem
SUPABASE_PUBLISHABLE_KEY: nenhuma rota atual precisa delas. Documentadas
em .env.example mesmo assim, para paralelismo com finance_app, mas como
reservadas/futuras — reduz a superfície de credenciais sensíveis que este
processo precisa ter em memória.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class ErroConfiguracao(RuntimeError):
    """Variável de ambiente obrigatória ausente."""


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise ErroConfiguracao(
            f"{nome} não definida. Copie backend/.env.example para backend/.env e configure."
        )
    return valor


def supabase_url() -> str:
    return _obrigatoria("SUPABASE_URL").rstrip("/")


def frontend_url() -> str:
    """Origem permitida para CORS. Padrão de desenvolvimento:
    http://localhost:3000 — nunca "*" (há rotas autenticadas)."""
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def ambiente() -> str:
    return os.getenv("AMBIENTE", "development")


def em_desenvolvimento() -> bool:
    return ambiente() != "production"
