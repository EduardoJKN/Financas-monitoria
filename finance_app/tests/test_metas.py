from datetime import date, timedelta
from decimal import Decimal

import pytest

from src import metas


def test_criar_buscar_listar_editar_excluir():
    meta_id = metas.criar_meta(
        nome="Reserva Pytest",
        data_inicio=date.today(),
        valor_alvo=Decimal("30000"),
        valor_atual=Decimal("12000"),
    )
    try:
        meta = metas.obter_meta(meta_id)
        assert meta is not None
        assert meta["concluida"] is False

        todas = metas.listar_metas()
        assert any(m["id"] == meta_id for m in todas)

        metas.atualizar_meta(meta_id, nome="Reserva Pytest Editada", valor_atual=Decimal("15000"))
        meta = metas.obter_meta(meta_id)
        assert meta["nome"] == "Reserva Pytest Editada"
        assert meta["valor_atual"] == Decimal("15000")
    finally:
        metas.excluir_meta(meta_id)
    assert metas.obter_meta(meta_id) is None


def test_valor_alvo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        metas.criar_meta(nome="Meta Inválida", data_inicio=date.today(), valor_alvo=Decimal("0"))


def test_valor_atual_negativo_levanta_erro():
    with pytest.raises(ValueError):
        metas.criar_meta(
            nome="Meta Inválida", data_inicio=date.today(), valor_alvo=Decimal("1000"),
            valor_atual=Decimal("-1"),
        )


def test_data_limite_anterior_ao_inicio_levanta_erro():
    with pytest.raises(ValueError):
        metas.criar_meta(
            nome="Meta Inválida",
            data_inicio=date.today(),
            valor_alvo=Decimal("1000"),
            data_limite=date.today() - timedelta(days=1),
        )


def test_meta_concluida_automaticamente_ao_atingir_alvo():
    meta_id = metas.criar_meta(
        nome="Meta Concluída Pytest", data_inicio=date.today(), valor_alvo=Decimal("1000"),
        valor_atual=Decimal("1000"),
    )
    try:
        meta = metas.obter_meta(meta_id)
        assert meta["concluida"] is True
    finally:
        metas.excluir_meta(meta_id)


def test_percentual_de_progresso():
    meta_id = metas.criar_meta(
        nome="Progresso Pytest", data_inicio=date.today(), valor_alvo=Decimal("30000"),
        valor_atual=Decimal("15000"),
    )
    try:
        progresso = metas.calcular_progresso_meta(meta_id)
        assert progresso["percentual"] == Decimal("50")
        assert progresso["valor_restante"] == Decimal("15000")
        assert progresso["concluida"] is False
    finally:
        metas.excluir_meta(meta_id)


def test_meta_acima_de_100_por_cento_nao_quebra_fica_limitada():
    meta_id = metas.criar_meta(
        nome="Acima do Alvo Pytest", data_inicio=date.today(), valor_alvo=Decimal("1000"),
        valor_atual=Decimal("1500"),
    )
    try:
        progresso = metas.calcular_progresso_meta(meta_id)
        assert progresso["percentual"] == Decimal("100")  # nunca passa de 100%
        assert progresso["valor_restante"] == Decimal("0")  # nunca fica negativo
        assert progresso["concluida"] is True
    finally:
        metas.excluir_meta(meta_id)
