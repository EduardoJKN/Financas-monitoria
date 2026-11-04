"""Cache em processo, de curta duração, para endpoints de analytics pesados.

REGRA ABSOLUTA: toda chave de cache inclui usuario_id — nunca é possível
um usuário receber um resultado calculado para outro. Sem Redis (não
necessário nesta fase); um dict em processo com TTL curto é suficiente
para o ganho real que se busca aqui (evitar recomputar o mesmo resumo em
poucos segundos, não servir dados "desatualizados" por muito tempo).

Invalidação: toda rota de mutação (criar/editar/excluir lançamento,
importar, pagar fatura, conciliar) chama `invalidar_usuario(usuario_id)`
antes de retornar, removendo todas as entradas daquele usuário — nunca
dependemos só do TTL para refletir uma mutação.
"""

from __future__ import annotations

import time
from threading import Lock

_TTL_PADRAO_SEGUNDOS = 15.0

_armazenamento: dict[str, tuple[float, object]] = {}
_trava = Lock()


def _chave(usuario_id: str, nome: str) -> str:
    return f"{usuario_id}:{nome}"


def obter(usuario_id: str, nome: str) -> object | None:
    with _trava:
        item = _armazenamento.get(_chave(usuario_id, nome))
        if item is None:
            return None
        expira_em, valor = item
        if time.monotonic() > expira_em:
            _armazenamento.pop(_chave(usuario_id, nome), None)
            return None
        return valor


def definir(usuario_id: str, nome: str, valor: object, ttl_segundos: float = _TTL_PADRAO_SEGUNDOS) -> None:
    with _trava:
        _armazenamento[_chave(usuario_id, nome)] = (time.monotonic() + ttl_segundos, valor)


def invalidar_usuario(usuario_id: str) -> None:
    """Remove todas as entradas de cache de um usuário — chamado após
    qualquer mutação que possa afetar analytics (lançamento, importação,
    pagamento de fatura, conciliação, etc.)."""
    prefixo = f"{usuario_id}:"
    with _trava:
        for chave in [k for k in _armazenamento if k.startswith(prefixo)]:
            _armazenamento.pop(chave, None)
