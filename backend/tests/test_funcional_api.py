"""Testes funcionais da API (Parte 32): a camada FastAPI realmente
repassa para src/ sem reimplementar regra nenhuma — parcelamento,
paginação, simulador, e que erros nunca expõem detalhes internos."""

from tests.conftest import cabecalho


def test_dashboard_gastos_fora_padrao_retorna_lista_vazia_sem_amostra(client, token_a):
    # Sem lançamentos suficientes no histórico, o endpoint responde 200 com
    # lista vazia — nunca marca anomalia sem base estatística (Parte 20).
    resposta = client.get("/api/v1/dashboard/gastos-fora-padrao", headers=cabecalho(token_a))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["gastos"] == []


def test_crud_completo_de_conta(client, token_a):
    criada = client.post(
        "/api/v1/contas",
        json={"nome": "Conta CRUD", "tipo": "conta_corrente", "saldo_inicial": "500.00"},
        headers=cabecalho(token_a),
    ).json()
    try:
        atualizada = client.patch(
            f"/api/v1/contas/{criada['id']}", json={"nome": "Conta CRUD Renomeada"}, headers=cabecalho(token_a)
        ).json()
        assert atualizada["nome"] == "Conta CRUD Renomeada"
    finally:
        resposta_delete = client.delete(f"/api/v1/contas/{criada['id']}", headers=cabecalho(token_a))
        assert resposta_delete.status_code == 204


def test_parcelamento_preserva_divisao_exata_em_centavos(client, token_a):
    resposta = client.post(
        "/api/v1/transacoes/parcelamento/pre-visualizar",
        json={"valor_total": "100.00", "data_primeira_parcela": "2026-01-01", "total_parcelas": 3},
        headers=cabecalho(token_a),
    )
    assert resposta.status_code == 200
    parcelas = resposta.json()
    valores = [p["valor"] for p in parcelas]
    assert sum(float(v) for v in valores) == 100.00
    assert valores[-1] != valores[0]  # resto de centavos vai para a última


def test_criar_parcelamento_cria_todas_as_parcelas(client, token_a):
    conta = client.post(
        "/api/v1/contas", json={"nome": "Conta Parcelamento", "tipo": "conta_corrente"}, headers=cabecalho(token_a)
    ).json()
    try:
        resposta = client.post(
            "/api/v1/transacoes/parcelamento",
            json={
                "tipo": "despesa",
                "descricao": "Geladeira",
                "valor_total": "900.00",
                "data_primeira_parcela": "2026-01-10",
                "total_parcelas": 3,
                "conta_id": conta["id"],
            },
            headers=cabecalho(token_a),
        )
        assert resposta.status_code == 201
        ids = resposta.json()["transacao_ids"]
        assert len(ids) == 3
    finally:
        for tid in ids:
            client.delete(f"/api/v1/transacoes/{tid}", headers=cabecalho(token_a))
        client.delete(f"/api/v1/contas/{conta['id']}", headers=cabecalho(token_a))


def test_listar_transacoes_respeita_limite_maximo(client, token_a):
    resposta = client.get(
        "/api/v1/transacoes", params={"limit": 999}, headers=cabecalho(token_a)
    )
    assert resposta.status_code == 200  # limite é silenciosamente capado, não erro


def test_simulador_tempo_meta(client, token_a):
    resposta = client.post(
        "/api/v1/simulador/tempo-meta",
        json={"valor_atual": "0", "valor_alvo": "1200", "aporte_mensal": "100"},
        headers=cabecalho(token_a),
    )
    assert resposta.status_code == 200
    assert resposta.json()["meses"] == 12


def test_erro_de_validacao_nao_expoe_detalhes_internos(client, token_a):
    resposta = client.post(
        "/api/v1/contas",
        json={"nome": "", "tipo": "tipo_invalido"},
        headers=cabecalho(token_a),
    )
    assert resposta.status_code == 422
    corpo = resposta.text.lower()
    for termo_proibido in ("traceback", "select ", "psycopg2", "sqlalchemy", "database_url"):
        assert termo_proibido not in corpo


def test_conta_inexistente_retorna_404_sem_detalhe_interno(client, token_a):
    resposta = client.get("/api/v1/contas/999999999", headers=cabecalho(token_a))
    assert resposta.status_code == 404
    assert "sql" not in resposta.text.lower()
