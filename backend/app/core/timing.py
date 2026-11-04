"""Instrumentação simples de performance (Parte 6).

Mede o tempo total de cada requisição e, em desenvolvimento, expõe via
header `Server-Timing` + log estruturado. Nunca loga token, senha,
DATABASE_URL/APP_DATABASE_URL nem corpo de dados financeiros — apenas
método, caminho, status e duração.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import em_desenvolvimento

logger = logging.getLogger("financas.timing")


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inicio = time.perf_counter()
        resposta = await call_next(request)
        duracao_ms = (time.perf_counter() - inicio) * 1000

        if em_desenvolvimento():
            resposta.headers["Server-Timing"] = f"total;dur={duracao_ms:.1f}"
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                resposta.status_code,
                duracao_ms,
            )
        return resposta
