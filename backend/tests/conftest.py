"""Fixtures da suíte do backend.

Os tokens usados aqui são assinados com um par de chaves EC gerado só para
os testes (nunca os do Supabase real) — a fixture `_jwks_fake` troca a
busca do JWKS por um client falso que serve a chave pública de teste,
permitindo testar o caminho REAL de validação (assinatura, exp, aud) sem
depender de rede nem de usuários reais no Supabase Auth. Isso também evita
criar qualquer conta/usuário real/órfão no projeto Supabase só para testar
a API — o pedido explícito de não deixar resíduo é respeitado também aqui.

Usuários "A" e "B" são UUIDs aleatórios por sessão de teste; cada teste que
cria dados é responsável por limpá-los (mesmo padrão já usado em
finance_app/tests)."""

import time
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import jwt as pyjwt

from app.core import security
from app.main import app

_CHAVE_PRIVADA_TESTE = ec.generate_private_key(ec.SECP256R1())
_CHAVE_PUBLICA_TESTE = _CHAVE_PRIVADA_TESTE.public_key()

_PRIVATE_PEM = _CHAVE_PRIVADA_TESTE.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_PUBLIC_PEM = _CHAVE_PUBLICA_TESTE.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# Chave DIFERENTE, usada só para gerar tokens com assinatura inválida.
_CHAVE_PRIVADA_INTRUSA = ec.generate_private_key(ec.SECP256R1())
_PRIVATE_PEM_INTRUSA = _CHAVE_PRIVADA_INTRUSA.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


class _ChaveFalsa:
    def __init__(self, chave):
        self.key = chave


class _JWKClientFalso:
    def get_signing_key_from_jwt(self, token):
        return _ChaveFalsa(_PUBLIC_PEM)


@pytest.fixture(autouse=True)
def _jwks_fake(monkeypatch):
    monkeypatch.setattr(security, "_obter_jwk_client", lambda: _JWKClientFalso())


def criar_token(
    sub: str,
    *,
    exp_delta_segundos: int = 3600,
    aud: str = "authenticated",
    chave_privada=None,
) -> str:
    agora = int(time.time())
    claims = {
        "sub": sub,
        "aud": aud,
        "iss": "https://exemplo-teste.supabase.co/auth/v1",
        "iat": agora,
        "exp": agora + exp_delta_segundos,
        "role": "authenticated",
    }
    return pyjwt.encode(claims, chave_privada or _PRIVATE_PEM, algorithm="ES256")


def token_assinatura_invalida(sub: str) -> str:
    return criar_token(sub, chave_privada=_PRIVATE_PEM_INTRUSA)


def cabecalho(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def usuario_a_id():
    return str(uuid.uuid4())


@pytest.fixture
def usuario_b_id():
    return str(uuid.uuid4())


@pytest.fixture
def token_a(usuario_a_id):
    return criar_token(usuario_a_id)


@pytest.fixture
def token_b(usuario_b_id):
    return criar_token(usuario_b_id)
