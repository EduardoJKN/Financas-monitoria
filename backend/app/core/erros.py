"""Tratamento central de erros (Parte 27 do lado do backend).

Nunca expõe SQL, traceback, connection string, credenciais ou detalhes
internos na resposta — mesma política já seguida pelo Streamlit
(src/banco_de_dados.py encapsula toda falha de driver/SQLAlchemy em
ErroBancoDeDados com mensagem genérica antes de propagar)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.banco_de_dados import ErroBancoDeDados

logger = logging.getLogger("financas.erros")


def registrar_handlers_erro(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def _handler_valor_invalido(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ErroBancoDeDados)
    async def _handler_erro_banco(request: Request, exc: ErroBancoDeDados) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _handler_generico(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Erro interno inesperado. Tente novamente."}
        )
