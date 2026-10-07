"""Autenticação via Supabase Auth (GoTrue).

A aplicação nunca armazena nem valida senha: toda credencial é enviada
direto para a API de autenticação do Supabase (HTTPS) e a aplicação só lida
com o resultado (tokens de sessão e dados do usuário). Usa `requests`
(dependência já existente) em vez do SDK `supabase-py` para não adicionar
uma árvore de dependências pesada (httpx/gotrue/postgrest/realtime/storage3)
só para três chamadas de API simples.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_TIMEOUT_SEGUNDOS = 10


class ErroAutenticacao(Exception):
    """Erro de autenticação com mensagem segura para exibir ao usuário.

    Nunca propaga o corpo bruto da resposta HTTP (pode conter detalhes
    internos do provedor); sempre extrai apenas uma mensagem amigável.
    """


def _config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not chave:
        raise ErroAutenticacao(
            "Autenticação não configurada. Defina SUPABASE_URL e "
            "SUPABASE_PUBLISHABLE_KEY no arquivo .env."
        )
    return url.rstrip("/"), chave


def _opcoes_redirect() -> dict:
    """Monta o options.email_redirect_to a partir de APP_URL (variável de
    ambiente — nunca uma URL fixa no código). Sem APP_URL configurada,
    retorna vazio e o Supabase usa o Site URL configurado no painel do
    projeto como fallback — nunca quebra por falta dessa variável."""
    app_url = os.getenv("APP_URL")
    if not app_url or not app_url.strip():
        return {}
    return {"email_redirect_to": app_url.strip().rstrip("/")}


def _extrair_mensagem(resposta: requests.Response) -> str:
    try:
        corpo = resposta.json()
    except ValueError:
        return "Não foi possível completar a operação. Tente novamente."
    mensagem = corpo.get("error_description") or corpo.get("msg") or corpo.get("error")
    if isinstance(mensagem, str) and mensagem.strip():
        return mensagem
    return "Não foi possível completar a operação. Tente novamente."


def _post(caminho: str, payload: dict, cabecalhos_extra: dict | None = None) -> dict:
    url_base, chave = _config()
    cabecalhos = {
        "apikey": chave,
        "Content-Type": "application/json",
        **(cabecalhos_extra or {}),
    }
    try:
        resposta = requests.post(
            f"{url_base}/auth/v1/{caminho}",
            json=payload,
            headers=cabecalhos,
            timeout=_TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as exc:
        raise ErroAutenticacao(
            "Não foi possível contatar o serviço de autenticação. Verifique sua conexão."
        ) from exc

    if resposta.status_code >= 400:
        raise ErroAutenticacao(_extrair_mensagem(resposta))

    try:
        return resposta.json()
    except ValueError:
        return {}


def cadastrar(email: str, senha: str) -> dict:
    """Cria um novo usuário. Retorna o corpo da resposta do Supabase Auth —
    pode ou não incluir sessão imediata (access_token), dependendo da
    configuração de confirmação de e-mail do projeto.

    Informa explicitamente email_redirect_to (via APP_URL) quando
    configurada, em vez de depender só do Site URL do projeto — importante
    porque o Site URL é uma configuração única por projeto Supabase, e esta
    aplicação pode rodar em mais de um ambiente (local, produção) com o
    mesmo projeto. Sem APP_URL, o Site URL do painel continua valendo."""
    if not email or not email.strip():
        raise ValueError("Informe um e-mail.")
    if not senha or len(senha) < 6:
        raise ValueError("A senha deve ter ao menos 6 caracteres.")
    payload = {"email": email.strip(), "password": senha}
    opcoes = _opcoes_redirect()
    if opcoes:
        payload["options"] = opcoes
    return _post("signup", payload)


def entrar(email: str, senha: str) -> dict:
    """Autentica um usuário existente. Retorna dict com access_token,
    refresh_token e user (contendo ao menos id e email)."""
    if not email or not email.strip():
        raise ValueError("Informe um e-mail.")
    if not senha:
        raise ValueError("Informe a senha.")
    return _post(
        "token?grant_type=password", {"email": email.strip(), "password": senha}
    )


def reenviar_confirmacao(email: str) -> None:
    """Reenvia o e-mail de confirmação de cadastro — útil quando a conta
    ainda não foi confirmada ou o link anterior expirou. Usa o endpoint
    oficial de resend do Supabase Auth (/auth/v1/resend, type='signup'),
    com o mesmo email_redirect_to de cadastrar(). Não revela se o e-mail
    existe ou já está confirmado (mesma política de privacidade de
    solicitar_recuperacao_senha)."""
    if not email or not email.strip():
        raise ValueError("Informe um e-mail.")
    payload = {"type": "signup", "email": email.strip()}
    opcoes = _opcoes_redirect()
    if opcoes:
        payload["options"] = opcoes
    _post("resend", payload)


def email_nao_confirmado(mensagem_erro: str) -> bool:
    """Heurística para detectar, a partir da mensagem de erro de entrar(),
    se a falha de login foi por e-mail ainda não confirmado (em vez de
    senha errada, por exemplo) — usada para oferecer o reenvio de
    confirmação no lugar certo da tela de login."""
    return "confirm" in (mensagem_erro or "").lower()


def solicitar_recuperacao_senha(email: str) -> None:
    """Dispara o e-mail de redefinição de senha. Não levanta erro quando o
    e-mail não existe (comportamento do próprio Supabase Auth, por design,
    para não revelar quais e-mails estão cadastrados)."""
    if not email or not email.strip():
        raise ValueError("Informe um e-mail.")
    _post("recover", {"email": email.strip()})


def sair(access_token: str) -> None:
    """Invalida a sessão no servidor. Erros aqui não devem impedir o logout
    local (a página sempre limpa a sessão local independentemente)."""
    if not access_token:
        return
    try:
        _post("logout?scope=local", {}, cabecalhos_extra={"Authorization": f"Bearer {access_token}"})
    except ErroAutenticacao:
        pass


def obter_usuario(access_token: str) -> dict:
    """Valida access_token contra o Supabase Auth (GET /auth/v1/user) e
    retorna os dados atuais do usuário. Levanta ErroAutenticacao se o
    token estiver expirado, inválido ou revogado — é assim que a
    aplicação descobre que uma sessão não é mais válida, em vez de
    assumir que ela continua boa só porque está em st.session_state."""
    url_base, chave = _config()
    try:
        resposta = requests.get(
            f"{url_base}/auth/v1/user",
            headers={"apikey": chave, "Authorization": f"Bearer {access_token}"},
            timeout=_TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as exc:
        raise ErroAutenticacao(
            "Não foi possível validar a sessão. Verifique sua conexão."
        ) from exc

    if resposta.status_code >= 400:
        raise ErroAutenticacao(_extrair_mensagem(resposta))

    try:
        return resposta.json()
    except ValueError:
        raise ErroAutenticacao("Resposta inválida ao validar a sessão.")


def renovar_sessao(refresh_token: str) -> dict:
    """Troca um refresh_token por uma nova sessão (novo access_token e
    refresh_token). Levanta ErroAutenticacao se o refresh_token também
    estiver inválido/expirado/revogado — nesse caso não há mais como
    renovar e a sessão deve ser encerrada (novo login é necessário)."""
    if not refresh_token:
        raise ErroAutenticacao("Sessão sem refresh_token; faça login novamente.")
    return _post("token?grant_type=refresh_token", {"refresh_token": refresh_token})


def validar_ou_renovar_sessao(sessao: dict) -> dict | None:
    """Confirma que a sessão ainda é válida no Supabase Auth, tentando
    renovar via refresh_token se o access_token estiver expirado/revogado.

    Retorna a sessão (possivelmente renovada, com o usuário atualizado) ou
    None quando não há mais nenhuma sessão válida — nesse caso o chamador
    deve tratar como logout (limpar a sessão local e exigir novo login).
    Nunca loga nem imprime o conteúdo de access_token/refresh_token.
    """
    access_token = sessao.get("access_token")
    if not access_token:
        return None

    try:
        usuario_atual = obter_usuario(access_token)
        return {**sessao, "user": usuario_atual}
    except ErroAutenticacao:
        pass  # access_token expirado/inválido/revogado: tenta renovar

    refresh_token = sessao.get("refresh_token")
    if not refresh_token:
        return None
    try:
        nova_sessao = renovar_sessao(refresh_token)
    except ErroAutenticacao:
        return None  # refresh_token também inválido: não há como renovar

    if not nova_sessao.get("access_token") or not nova_sessao.get("user"):
        return None
    return nova_sessao
