"""Testes de src/auth.py — autenticação via Supabase Auth.

Usa mocks de requests (nunca bate na rede real): o foco aqui é a lógica de
validação/renovação de sessão (token expirado, refresh, revogação), não o
comportamento do Supabase em si. Garante também que nenhum teste imprime ou
loga o conteúdo de um token.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src import auth


@pytest.fixture(autouse=True)
def _config_supabase_fake(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "chave-fake-teste")
    # Garante estado limpo independente do que estiver no .env real do
    # ambiente — cada teste que precisa de APP_URL define explicitamente.
    monkeypatch.delenv("APP_URL", raising=False)


def _resposta(status_code: int, corpo: dict) -> MagicMock:
    resposta = MagicMock()
    resposta.status_code = status_code
    resposta.json.return_value = corpo
    return resposta


SESSAO_VALIDA = {
    "access_token": "access-valido",
    "refresh_token": "refresh-valido",
    "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "a@exemplo.com"},
}


# ---------------------------------------------------------------------
# obter_usuario / renovar_sessao — chamadas isoladas
# ---------------------------------------------------------------------
def test_obter_usuario_token_valido_retorna_usuario():
    with patch("src.auth.requests.get") as mock_get:
        mock_get.return_value = _resposta(200, {"id": "u1", "email": "a@exemplo.com"})
        usuario = auth.obter_usuario("token-valido")
    assert usuario["id"] == "u1"


def test_obter_usuario_token_expirado_levanta_erro():
    with patch("src.auth.requests.get") as mock_get:
        mock_get.return_value = _resposta(401, {"error_description": "JWT expired"})
        with pytest.raises(auth.ErroAutenticacao):
            auth.obter_usuario("token-expirado")


def test_obter_usuario_falha_rede_levanta_erro_amigavel():
    import requests as requests_modulo

    with patch("src.auth.requests.get", side_effect=requests_modulo.ConnectionError("boom")):
        with pytest.raises(auth.ErroAutenticacao):
            auth.obter_usuario("token-qualquer")


def test_renovar_sessao_sem_refresh_token_levanta_erro():
    with pytest.raises(auth.ErroAutenticacao):
        auth.renovar_sessao("")


def test_renovar_sessao_valida_retorna_nova_sessao():
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(
            200,
            {
                "access_token": "novo-access",
                "refresh_token": "novo-refresh",
                "user": {"id": "u1", "email": "a@exemplo.com"},
            },
        )
        nova_sessao = auth.renovar_sessao("refresh-valido")
    assert nova_sessao["access_token"] == "novo-access"


def test_renovar_sessao_refresh_token_revogado_levanta_erro():
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(401, {"error_description": "Invalid Refresh Token"})
        with pytest.raises(auth.ErroAutenticacao):
            auth.renovar_sessao("refresh-revogado")


# ---------------------------------------------------------------------
# validar_ou_renovar_sessao — a função que o app.py chama a cada TTL
# ---------------------------------------------------------------------
def test_validar_ou_renovar_sessao_sem_access_token_retorna_none():
    assert auth.validar_ou_renovar_sessao({}) is None


def test_validar_ou_renovar_sessao_token_valido_mantem_sessao():
    with patch("src.auth.requests.get") as mock_get:
        mock_get.return_value = _resposta(200, {"id": "u1", "email": "a@exemplo.com"})
        resultado = auth.validar_ou_renovar_sessao(SESSAO_VALIDA)
    assert resultado["access_token"] == "access-valido"
    assert resultado["user"]["id"] == "u1"


def test_validar_ou_renovar_sessao_token_expirado_renova_com_sucesso():
    with patch("src.auth.requests.get") as mock_get, patch("src.auth.requests.post") as mock_post:
        mock_get.return_value = _resposta(401, {"error_description": "JWT expired"})
        mock_post.return_value = _resposta(
            200,
            {
                "access_token": "novo-access",
                "refresh_token": "novo-refresh",
                "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "a@exemplo.com"},
            },
        )
        resultado = auth.validar_ou_renovar_sessao(SESSAO_VALIDA)
    assert resultado is not None
    assert resultado["access_token"] == "novo-access"


def test_validar_ou_renovar_sessao_token_e_refresh_revogados_retorna_none():
    """Caso central da correção: access_token expirado/revogado E
    refresh_token também inválido -> a sessão deixa de valer. O usuário
    não pode continuar acessando dados só porque "sessao" ainda está em
    st.session_state."""
    with patch("src.auth.requests.get") as mock_get, patch("src.auth.requests.post") as mock_post:
        mock_get.return_value = _resposta(401, {"error_description": "JWT expired"})
        mock_post.return_value = _resposta(401, {"error_description": "Invalid Refresh Token"})
        resultado = auth.validar_ou_renovar_sessao(SESSAO_VALIDA)
    assert resultado is None


def test_validar_ou_renovar_sessao_sem_refresh_token_nao_tenta_renovar():
    sessao_sem_refresh = {"access_token": "access-expirado", "user": SESSAO_VALIDA["user"]}
    with patch("src.auth.requests.get") as mock_get, patch("src.auth.requests.post") as mock_post:
        mock_get.return_value = _resposta(401, {"error_description": "JWT expired"})
        resultado = auth.validar_ou_renovar_sessao(sessao_sem_refresh)
        mock_post.assert_not_called()
    assert resultado is None


# ---------------------------------------------------------------------
# Nenhum token é logado/impresso
# ---------------------------------------------------------------------
def test_nenhum_token_aparece_na_mensagem_de_erro(capsys):
    with patch("src.auth.requests.get") as mock_get:
        mock_get.return_value = _resposta(401, {"error_description": "JWT expired"})
        with pytest.raises(auth.ErroAutenticacao) as excinfo:
            auth.obter_usuario("segredo-nao-deve-aparecer-em-lugar-nenhum")
    assert "segredo-nao-deve-aparecer-em-lugar-nenhum" not in str(excinfo.value)
    capturado = capsys.readouterr()
    assert "segredo-nao-deve-aparecer-em-lugar-nenhum" not in capturado.out
    assert "segredo-nao-deve-aparecer-em-lugar-nenhum" not in capturado.err


# ---------------------------------------------------------------------
# Reenvio de confirmação de e-mail
# ---------------------------------------------------------------------
def test_reenviar_confirmacao_sem_email_levanta_erro():
    with pytest.raises(ValueError):
        auth.reenviar_confirmacao("")


def test_reenviar_confirmacao_chama_endpoint_resend_com_type_signup():
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(200, {})
        auth.reenviar_confirmacao("usuario@exemplo.com")

    url_chamada, kwargs = mock_post.call_args
    assert url_chamada[0].endswith("/auth/v1/resend")
    assert kwargs["json"] == {"type": "signup", "email": "usuario@exemplo.com"}


def test_reenviar_confirmacao_propaga_erro_do_servico():
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(400, {"error_description": "Email already confirmed"})
        with pytest.raises(auth.ErroAutenticacao):
            auth.reenviar_confirmacao("usuario@exemplo.com")


def test_email_nao_confirmado_detecta_mensagem_tipica():
    assert auth.email_nao_confirmado("Email not confirmed") is True
    assert auth.email_nao_confirmado("Invalid login credentials") is False
    assert auth.email_nao_confirmado("") is False
    assert auth.email_nao_confirmado(None) is False


# ---------------------------------------------------------------------
# email_redirect_to via APP_URL (nunca uma URL fixa de localhost no código)
# ---------------------------------------------------------------------
def test_cadastrar_sem_app_url_nao_envia_options():
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(200, {"access_token": None})
        auth.cadastrar("usuario@exemplo.com", "senha123")

    _, kwargs = mock_post.call_args
    assert "options" not in kwargs["json"]


def test_cadastrar_com_app_url_envia_email_redirect_to(monkeypatch):
    monkeypatch.setenv("APP_URL", "http://localhost:8501")
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(200, {"access_token": None})
        auth.cadastrar("usuario@exemplo.com", "senha123")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["options"] == {"email_redirect_to": "http://localhost:8501"}


def test_reenviar_confirmacao_com_app_url_envia_email_redirect_to(monkeypatch):
    monkeypatch.setenv("APP_URL", "https://meuapp.exemplo.com/")
    with patch("src.auth.requests.post") as mock_post:
        mock_post.return_value = _resposta(200, {})
        auth.reenviar_confirmacao("usuario@exemplo.com")

    _, kwargs = mock_post.call_args
    # a barra final é removida para manter a URL consistente
    assert kwargs["json"]["options"] == {"email_redirect_to": "https://meuapp.exemplo.com"}
