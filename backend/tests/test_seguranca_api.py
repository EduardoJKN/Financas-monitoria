"""Testes de segurança da API (Partes 4/19 da migração).

Prova que: sem token -> 401; token inválido/sem assinatura válida -> 401;
token expirado -> 401; e que um usuário autenticado só acessa os PRÓPRIOS
dados em contas, categorias, transações (incluindo tentativa de referenciar
conta de outro usuário por ID conhecido), cartões, metas e no dashboard de
analytics — nunca os de outro usuário, mesmo por ID conhecido.
"""

from decimal import Decimal

from tests.conftest import cabecalho, criar_token, token_assinatura_invalida

ROTAS_PROTEGIDAS = [
    ("GET", "/api/v1/contas"),
    ("GET", "/api/v1/categorias"),
    ("GET", "/api/v1/transacoes"),
    ("GET", "/api/v1/cartoes"),
    ("GET", "/api/v1/metas"),
    ("GET", "/api/v1/dashboard/resumo"),
    ("GET", "/api/v1/dashboard/gastos-fora-padrao"),
]


# ---------------------------------------------------------------------
# Autenticação: sem token / token inválido / expirado / assinatura errada
# ---------------------------------------------------------------------
def test_sem_token_retorna_401(client):
    for metodo, rota in ROTAS_PROTEGIDAS:
        resposta = client.request(metodo, rota)
        assert resposta.status_code == 401, rota


def test_token_malformado_retorna_401(client):
    resposta = client.get("/api/v1/contas", headers={"Authorization": "Bearer nao-e-um-jwt"})
    assert resposta.status_code == 401


def test_header_sem_bearer_retorna_401(client):
    resposta = client.get("/api/v1/contas", headers={"Authorization": "Token abc"})
    assert resposta.status_code == 401


def test_token_assinatura_invalida_retorna_401(client, usuario_a_id):
    token_falso = token_assinatura_invalida(usuario_a_id)
    resposta = client.get("/api/v1/contas", headers=cabecalho(token_falso))
    assert resposta.status_code == 401


def test_token_expirado_retorna_401(client, usuario_a_id):
    # -10s ficaria dentro da tolerância de clock skew (_LEEWAY_SEGUNDOS=60 em
    # app/core/security.py, que existe para não rejeitar tokens recém-emitidos
    # por causa da diferença real de relógio entre este servidor e o Supabase)
    # — por isso o token aqui expira bem além da folga, para continuar
    # testando "expirado de verdade", não a tolerância legítima.
    token_expirado = criar_token(usuario_a_id, exp_delta_segundos=-120)
    resposta = client.get("/api/v1/contas", headers=cabecalho(token_expirado))
    assert resposta.status_code == 401


def test_token_audience_errada_retorna_401(client, usuario_a_id):
    token_errado = criar_token(usuario_a_id, aud="outro-publico")
    resposta = client.get("/api/v1/contas", headers=cabecalho(token_errado))
    assert resposta.status_code == 401


def test_health_nao_exige_autenticacao(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200


# ---------------------------------------------------------------------
# Usuário válido só acessa os próprios dados — Contas
# ---------------------------------------------------------------------
def test_usuario_valido_cria_e_le_propria_conta(client, token_a):
    resposta = client.post(
        "/api/v1/contas",
        json={"nome": "Conta Segura A", "tipo": "conta_corrente", "saldo_inicial": "100.00"},
        headers=cabecalho(token_a),
    )
    assert resposta.status_code == 201
    conta_id = resposta.json()["id"]
    try:
        resposta_get = client.get(f"/api/v1/contas/{conta_id}", headers=cabecalho(token_a))
        assert resposta_get.status_code == 200
        assert resposta_get.json()["nome"] == "Conta Segura A"
    finally:
        client.delete(f"/api/v1/contas/{conta_id}", headers=cabecalho(token_a))


def test_usuario_b_nao_lista_conta_de_a(client, token_a, token_b):
    criada = client.post(
        "/api/v1/contas",
        json={"nome": "Conta Privada A", "tipo": "conta_corrente"},
        headers=cabecalho(token_a),
    ).json()
    try:
        contas_de_b = client.get("/api/v1/contas", headers=cabecalho(token_b)).json()
        assert all(c["nome"] != "Conta Privada A" for c in contas_de_b)
    finally:
        client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))


def test_usuario_b_nao_obtem_conta_de_a_por_id_conhecido(client, token_a, token_b):
    criada = client.post(
        "/api/v1/contas", json={"nome": "Conta X", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.get(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_b))
        assert resposta.status_code == 404
    finally:
        client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))


def test_usuario_b_nao_altera_conta_de_a(client, token_a, token_b):
    criada = client.post(
        "/api/v1/contas", json={"nome": "Conta Y", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.patch(
            f"/api/v1/contas/{criada['id']}", json={"nome": "Hackeado"}, headers=cabecalho(token_b)
        )
        assert resposta.status_code != 200

        intacta = client.get(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a)).json()
        assert intacta["nome"] == "Conta Y"
    finally:
        client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))


def test_usuario_b_nao_exclui_conta_de_a(client, token_a, token_b):
    criada = client.post(
        "/api/v1/contas", json={"nome": "Conta Z", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_b))
        assert resposta.status_code != 204

        ainda_existe = client.get(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))
        assert ainda_existe.status_code == 200
    finally:
        client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))


# ---------------------------------------------------------------------
# Categorias
# ---------------------------------------------------------------------
def test_usuario_b_nao_acessa_categoria_de_a(client, token_a, token_b):
    criada = client.post(
        "/api/v1/categorias", json={"nome": "Categoria Segura A", "tipo": "despesa"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.get(f"/api/v1/categorias/{criada['id']}", headers=cabecalho(token_b))
        assert resposta.status_code == 404

        lista_b = client.get("/api/v1/categorias", headers=cabecalho(token_b)).json()
        assert all(c["id"] != criada["id"] for c in lista_b)
    finally:
        client.delete(f"/api/v1/categorias/{criada['id']}", headers=cabecalho(token_a))


# ---------------------------------------------------------------------
# Transações — inclui tentativa de criar usando conta_id de outro usuário
# ---------------------------------------------------------------------
def test_usuario_b_nao_cria_transacao_usando_conta_de_a(client, token_a, token_b):
    conta_a = client.post(
        "/api/v1/contas", json={"nome": "Conta Transacao A", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.post(
            "/api/v1/transacoes",
            json={
                "tipo": "despesa",
                "descricao": "Ataque via conta_id conhecido",
                "valor": "10.00",
                "data_transacao": "2026-10-01",
                "conta_id": conta_a["id"],
            },
            headers=cabecalho(token_b),
        )
        assert resposta.status_code != 201

        transacoes_na_conta_a = client.get(
            "/api/v1/transacoes", params={"conta_id": conta_a["id"]}, headers=cabecalho(token_a)
        ).json()
        assert transacoes_na_conta_a == []
    finally:
        client.delete(f"/api/v1/contas/{conta_a['id']}", headers=cabecalho(token_a))


def test_usuario_b_nao_ve_transacao_de_a(client, token_a, token_b):
    conta_a = client.post(
        "/api/v1/contas", json={"nome": "Conta Transacao A2", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    transacao_a = client.post(
        "/api/v1/transacoes",
        json={
            "tipo": "despesa",
            "descricao": "Despesa privada de A",
            "valor": "50.00",
            "data_transacao": "2026-10-01",
            "conta_id": conta_a["id"],
        },
        headers=cabecalho(token_a),
    ).json()
    try:
        resposta = client.get(f"/api/v1/transacoes/{transacao_a['id']}", headers=cabecalho(token_b))
        assert resposta.status_code == 404
    finally:
        client.delete(f"/api/v1/transacoes/{transacao_a['id']}", headers=cabecalho(token_a))
        client.delete(f"/api/v1/contas/{conta_a['id']}", headers=cabecalho(token_a))


# ---------------------------------------------------------------------
# Cartões
# ---------------------------------------------------------------------
def test_usuario_b_nao_acessa_cartao_de_a(client, token_a, token_b):
    cartao_a = client.post(
        "/api/v1/cartoes",
        json={"nome": "Cartao Seguro A", "limite": "1000.00", "dia_fechamento": 10, "dia_vencimento": 20},
        headers=cabecalho(token_a),
    ).json()
    try:
        resposta = client.get(f"/api/v1/cartoes/{cartao_a['id']}", headers=cabecalho(token_b))
        assert resposta.status_code == 404

        lista_b = client.get("/api/v1/cartoes", headers=cabecalho(token_b)).json()
        assert all(c["id"] != cartao_a["id"] for c in lista_b)
    finally:
        client.delete(f"/api/v1/cartoes/{cartao_a['id']}", headers=cabecalho(token_a))


# ---------------------------------------------------------------------
# Metas
# ---------------------------------------------------------------------
def test_usuario_b_nao_acessa_meta_de_a(client, token_a, token_b):
    meta_a = client.post(
        "/api/v1/metas",
        json={"nome": "Meta Segura A", "data_inicio": "2026-01-01", "valor_alvo": "1000.00"},
        headers=cabecalho(token_a),
    ).json()
    try:
        resposta = client.get(f"/api/v1/metas/{meta_a['id']}", headers=cabecalho(token_b))
        assert resposta.status_code == 404
    finally:
        client.delete(f"/api/v1/metas/{meta_a['id']}", headers=cabecalho(token_a))


# ---------------------------------------------------------------------
# Analytics / dashboard — nunca mistura dados de dois usuários
# ---------------------------------------------------------------------
def test_dashboard_isolado_por_usuario(client, token_a, token_b):
    conta_a = client.post(
        "/api/v1/contas", json={"nome": "Conta Dash A", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    categoria_a = client.post(
        "/api/v1/categorias", json={"nome": "Categoria Dash A", "tipo": "despesa"}, headers=cabecalho(token_a)
    ).json()
    transacao_a = client.post(
        "/api/v1/transacoes",
        json={
            "tipo": "despesa",
            "descricao": "Despesa grande de A",
            "valor": "999999.00",
            "data_transacao": "2026-10-01",
            "conta_id": conta_a["id"],
            "categoria_id": categoria_a["id"],
        },
        headers=cabecalho(token_a),
    ).json()
    try:
        resumo_b = client.get("/api/v1/dashboard/resumo", headers=cabecalho(token_b)).json()
        assert Decimal(str(resumo_b["despesas"])) < Decimal("999999.00")
        assert all(
            d["categoria"] != "Categoria Dash A" for d in resumo_b.get("maiores_despesas", [])
        )
    finally:
        client.delete(f"/api/v1/transacoes/{transacao_a['id']}", headers=cabecalho(token_a))
        client.delete(f"/api/v1/categorias/{categoria_a['id']}", headers=cabecalho(token_a))
        client.delete(f"/api/v1/contas/{conta_a['id']}", headers=cabecalho(token_a))
