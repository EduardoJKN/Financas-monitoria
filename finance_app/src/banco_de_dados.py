import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

load_dotenv()


class ErroBancoDeDados(Exception):
    """Erro genérico da camada de acesso a dados.

    Usada para encapsular falhas do driver/SQLAlchemy sem propagar a
    mensagem original (que pode conter detalhes de conexão) para quem
    chama a camada de acesso a dados.
    """


class ErroContextoUsuario(ErroBancoDeDados):
    """Levantada quando uma operação de banco user-scoped é tentada sem um
    usuário autenticado definido no contexto atual (definir_usuario_atual()
    precisa ser chamado antes, logo após validar a sessão de login)."""


# ---------------------------------------------------------------------
# Contexto do usuário autenticado (um por execução de página/requisição)
# ---------------------------------------------------------------------
_usuario_atual: ContextVar[str | None] = ContextVar("usuario_atual", default=None)

# Conexão compartilhada opcional (ver transacao_compartilhada()) — None
# significa "sem otimização ativa", comportamento 100% inalterado.
_conexao_compartilhada: ContextVar[Connection | None] = ContextVar(
    "conexao_compartilhada", default=None
)


def definir_usuario_atual(usuario_id) -> None:
    """Define o usuário autenticado do contexto atual. Toda página que
    acessa dados user-scoped deve chamar isto uma vez, logo após confirmar
    a sessão autenticada (ver src/auth.py)."""
    _usuario_atual.set(str(usuario_id) if usuario_id is not None else None)


def obter_usuario_atual() -> str | None:
    return _usuario_atual.get()


def _montar_url(variavel: str) -> str:
    url = os.getenv(variavel)
    if not url:
        raise ValueError(
            f"{variavel} não definida. Copie .env.example para .env e configure a conexão."
        )
    if url.startswith("postgresql://"):
        # Força o driver psycopg2 (instalado via requirements.txt) em vez de
        # depender da resolução implícita de driver do SQLAlchemy, que pode
        # variar entre versões.
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def obter_url_banco_de_dados() -> str:
    """URL administrativa (DATABASE_URL): role com privilégio de DDL, que
    também contorna RLS (ver migration 0005). Usada pelo Alembic e por
    operações administrativas estreitas e auditadas (ex.: reivindicação de
    dados legados em src/migracao_legado.py). NUNCA usar para servir dados
    de um usuário autenticado — use conexao_usuario() para isso."""
    return _montar_url("DATABASE_URL")


def obter_url_banco_de_dados_app() -> str:
    """URL de execução da aplicação (APP_DATABASE_URL): role restrita
    (app_runtime), sem BYPASSRLS, de fato sujeita às políticas de RLS."""
    return _montar_url("APP_DATABASE_URL")


@lru_cache(maxsize=1)
def obter_engine() -> Engine:
    return create_engine(obter_url_banco_de_dados(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def obter_engine_app() -> Engine:
    return create_engine(obter_url_banco_de_dados_app(), pool_pre_ping=True)


def testar_conexao() -> bool:
    try:
        with obter_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@contextmanager
def conexao_usuario() -> Connection:
    """Conexão de banco com o contexto do usuário autenticado já aplicado.

    É o único jeito suportado de qualquer módulo em src/ acessar dados
    user-scoped: toda consulta feita aqui é automaticamente restrita pelo
    PostgreSQL (RLS) às linhas do usuário atual — não depende de nenhuma
    cláusula WHERE adicional no código Python. Levanta ErroContextoUsuario
    se nenhum usuário estiver definido no contexto atual.

    Se chamada dentro de um bloco `with transacao_compartilhada():`,
    reaproveita a conexão já aberta em vez de abrir uma nova — ver essa
    função para o motivo (reduz round-trips de rede em endpoints que
    agregam várias consultas, ex.: dashboard). Fora desse bloco (o caso
    comum, incluindo todo o Streamlit), o comportamento é exatamente o de
    sempre: uma conexão nova por chamada.
    """
    usuario_id = _usuario_atual.get()
    if not usuario_id:
        raise ErroContextoUsuario(
            "Nenhum usuário autenticado no contexto atual. Faça login antes "
            "de acessar dados."
        )

    conexao_existente = _conexao_compartilhada.get()
    if conexao_existente is not None:
        yield conexao_existente
        return

    with obter_engine_app().begin() as conn:
        conn.execute(
            text("SELECT set_config('app.usuario_id', :uid, true)"), {"uid": usuario_id}
        )
        yield conn


@contextmanager
def transacao_compartilhada() -> Connection:
    """Otimização de transporte, opcional e aditiva: abre UMA conexão e a
    disponibiliza para todas as chamadas de conexao_usuario() feitas
    dentro deste bloco, em vez de cada uma abrir sua própria conexão —
    medido em produção, cada round-trip ao Postgres custa ~900ms de
    latência de rede neste ambiente, e endpoints agregados (ex.:
    dashboard) chamam conexao_usuario() internamente mais de dez vezes.

    Use apenas para fluxos SOMENTE LEITURA: como todas as chamadas
    aninhadas compartilham a mesma transação, uma falha em QUALQUER uma
    delas desfaz (rollback) tudo que foi feito no bloco — o que nunca é um
    problema para SELECTs, mas pode surpreender se usado com escritas
    independentes. Nunca muda isolamento por RLS: set_config continua
    sendo aplicado normalmente.
    """
    usuario_id = _usuario_atual.get()
    if not usuario_id:
        raise ErroContextoUsuario(
            "Nenhum usuário autenticado no contexto atual. Faça login antes "
            "de acessar dados."
        )
    with obter_engine_app().begin() as conn:
        conn.execute(
            text("SELECT set_config('app.usuario_id', :uid, true)"), {"uid": usuario_id}
        )
        token = _conexao_compartilhada.set(conn)
        try:
            yield conn
        finally:
            _conexao_compartilhada.reset(token)
