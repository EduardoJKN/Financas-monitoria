"""Validação de identidade da API — Parte 2 da migração.

ESTRATÉGIA ESCOLHIDA: validação JWT LOCAL via JWKS oficial do projeto
Supabase (preferência nº 1 do escopo, confirmada compatível: o projeto já
usa chaves assimétricas ES256 — testado em
`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`, que responde 200 com uma
chave EC pública). Isso significa validar assinatura, expiração e audience
inteiramente em memória, sem round-trip ao Supabase por requisição —
melhor latência que a alternativa (chamada remota a /auth/v1/user).

TRADE-OFF DOCUMENTADO: validação local detecta token expirado
imediatamente (claim "exp"), mas NÃO detecta revogação de sessão
(logout remoto, "sign out everywhere") antes do token expirar
naturalmente — isso é inerente a qualquer validação puramente local de
JWT, não uma lacuna desta implementação. O access_token do Supabase tem
vida curta por padrão (~1h), limitando a janela de exposição. Se no futuro
isso se mostrar insuficiente, a mitigação é reduzir o lifetime do token no
painel do Supabase ou adicionar uma checagem remota periódica (ver
finance_app/src/auth.py:validar_ou_renovar_sessao, que já faz isso no
Streamlit) — não implementado aqui agora para manter a solução simples,
como pedido.

NUNCA aceite identidade por X-User-ID, usuario_id em query/body, ou
qualquer outro meio informado pelo cliente. A única fonte de identidade é
o claim "sub" de um token com assinatura válida.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.core.config import supabase_url

logger = logging.getLogger("financas.auth")

_AUDIENCE = "authenticated"
_ALGORITMOS_ACEITOS = ["ES256"]
_JWKS_CACHE_SEGUNDOS = 3600  # chaves de assinatura trocam raramente
_LEEWAY_SEGUNDOS = 60  # tolerância a diferença de relógio entre este servidor e o Supabase
# (medido neste ambiente: ~23s de atraso no relógio local vs. o header Date
# retornado pelo próprio Supabase — 60s dá folga confortável sem enfraquecer
# a expiração real do token, que ainda vale por ~1h)

_jwk_client: PyJWKClient | None = None


class ErroAutenticacaoAPI(HTTPException):
    """401 padronizado — nunca inclui detalhes internos do token/erro."""

    def __init__(self, detalhe: str = "Sessão inválida ou expirada.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detalhe,
            headers={"WWW-Authenticate": "Bearer"},
        )


def _obter_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        jwks_url = f"{supabase_url()}/auth/v1/.well-known/jwks.json"
        _jwk_client = PyJWKClient(jwks_url, lifespan=_JWKS_CACHE_SEGUNDOS)
    return _jwk_client


def validar_token(token: str) -> dict:
    """Valida assinatura (JWKS), expiração e audience de um access_token
    do Supabase. Levanta ErroAutenticacaoAPI (401) se inválido/expirado/
    malformado. Retorna os claims decodificados em caso de sucesso."""
    if not token or not token.strip():
        raise ErroAutenticacaoAPI("Token de autenticação ausente.")
    try:
        chave_assinatura = _obter_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            chave_assinatura.key,
            algorithms=_ALGORITMOS_ACEITOS,
            audience=_AUDIENCE,
            options={"require": ["exp", "sub", "iat"]},
            leeway=_LEEWAY_SEGUNDOS,
        )
    except jwt.PyJWTError as exc:
        # Nunca propaga a mensagem interna da lib de JWT para o cliente
        # (pode conter detalhes da chave/claims) — mas registra no log do
        # servidor (só aqui), para diferenciar token expirado de uma falha
        # transitória ao buscar o JWKS (ex.: PyJWKClientConnectionError),
        # que de outra forma seria indistinguível de um 401 legítimo.
        logger.warning("Falha ao validar token: %s: %s", type(exc).__name__, exc)
        raise ErroAutenticacaoAPI("Sessão inválida ou expirada.")
    return claims


def obter_usuario_atual(authorization: str | None = Header(default=None)) -> str:
    """Dependency FastAPI: única forma suportada de identificar o usuário
    de uma requisição. Extrai e valida o Bearer token do header
    Authorization e retorna o usuario_id (claim 'sub'). Qualquer rota
    protegida deve depender desta função — nunca de um header/parâmetro
    definido pelo cliente."""
    if not authorization or not authorization.strip():
        raise ErroAutenticacaoAPI("Token de autenticação ausente.")
    partes = authorization.strip().split(" ", 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise ErroAutenticacaoAPI("Cabeçalho Authorization deve ser 'Bearer <token>'.")

    claims = validar_token(partes[1].strip())
    usuario_id = claims.get("sub")
    if not usuario_id:
        raise ErroAutenticacaoAPI("Token sem identificação de usuário.")
    return str(usuario_id)
