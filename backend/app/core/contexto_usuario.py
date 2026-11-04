"""Integração com o contexto de usuário de src/banco_de_dados.py (RLS).

DECISÃO DE ARQUITETURA — por que um decorator, e não confiar em
contextvars atravessando dependências do FastAPI:

`definir_usuario_atual()`/`conexao_usuario()` (finance_app/src/banco_de_dados.py)
usam uma `contextvars.ContextVar`. Isso é seguro dentro de uma única
execução síncrona (como o Streamlit, que roda cada rerun numa thread só) —
mas o FastAPI/Starlette pode executar uma dependency síncrona (`Depends`)
e o endpoint síncrono em invocações de thread-pool SEPARADAS (cada uma via
`anyio.to_thread.run_sync`, que copia o contexto de contextvars no momento
da chamada). Não há garantia documentada de que um `.set()` feito dentro
de uma dependency apareça no endpoint logo depois — depender disso seria
apostar em um detalhe de implementação, inaceitável para o mecanismo que
protege o isolamento entre usuários.

Por isso o desenho aqui é deliberadamente explícito e não ambíguo: o
FastAPI resolve `usuario_id` via `Depends(obter_usuario_atual)` (isso É
passagem de parâmetro comum, sem ambiguidade nenhuma) e o decorator abaixo
chama `definir_usuario_atual(usuario_id)` dentro da MESMA chamada de
função que, em seguida, invoca o corpo do endpoint — ou seja, sempre na
mesma thread/stack, nunca dependendo de propagação entre chamadas
separadas do FastAPI.
"""

from __future__ import annotations

import functools
from typing import Callable

from src.banco_de_dados import definir_usuario_atual


def com_usuario(func: Callable) -> Callable:
    """Decorator para endpoints protegidos: define o contexto de usuário
    (a partir do `usuario_id` já validado e injetado via
    `Depends(obter_usuario_atual)`) imediatamente antes de chamar o corpo
    do endpoint, e sempre limpa o contexto depois — mesmo em caso de
    erro."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        usuario_id = kwargs.get("usuario_id")
        if not usuario_id:
            # Defesa em profundidade: isto só aconteceria se um endpoint
            # usasse o decorator sem declarar o parâmetro usuario_id via
            # Depends(obter_usuario_atual) — erro de programação, não de
            # usuário. Falha explicitamente em vez de seguir sem contexto.
            raise RuntimeError(
                "com_usuario: endpoint não declarou usuario_id=Depends(obter_usuario_atual)."
            )
        definir_usuario_atual(usuario_id)
        try:
            return func(*args, **kwargs)
        finally:
            definir_usuario_atual(None)

    return wrapper
