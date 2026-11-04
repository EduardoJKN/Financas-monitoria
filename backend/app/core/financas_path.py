"""Bootstrap de import da camada de negócio existente.

DECISÃO DE ARQUITETURA (documentada também no README da migração):

O backend NÃO duplica nem copia a lógica financeira — ele reaproveita
diretamente o pacote `src/` já usado pelo Streamlit (`finance_app/src/`).
Mover ou reempacotar esse código foi avaliado e descartado por ser mais
arriscado do que necessário: o Streamlit depende dele hoje e qualquer
reorganização poderia quebrá-lo sem necessidade. Em vez disso, este módulo
apenas adiciona `finance_app/` ao sys.path, exatamente como
`migrations/env.py` já faz para o Alembic — uma técnica já estabelecida
neste projeto, não uma novidade.

A partir daqui, `from src import contas`, `from src import transacoes` etc.
resolvem para o MESMO código-fonte que o Streamlit usa. Uma alteração de
regra de negócio feita em finance_app/src vale para os dois, sem
duplicação.

Deve ser importado antes de qualquer `from src import ...` no backend —
por isso é importado logo no topo de app/__init__.py.
"""

import sys
from pathlib import Path

_RAIZ_REPO = Path(__file__).resolve().parents[3]
_FINANCE_APP_DIR = _RAIZ_REPO / "finance_app"

if not _FINANCE_APP_DIR.is_dir():
    raise RuntimeError(
        f"Diretório finance_app/ não encontrado em {_FINANCE_APP_DIR}. "
        "O backend depende do pacote src/ existente nesse diretório."
    )

_caminho = str(_FINANCE_APP_DIR)
if _caminho not in sys.path:
    sys.path.insert(0, _caminho)
