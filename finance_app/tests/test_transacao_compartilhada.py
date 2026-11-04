"""Testes de transacao_compartilhada() (src/banco_de_dados.py) — otimização
opcional e aditiva de transporte (Parte 6 da migração para FastAPI/Next.js):
reaproveita uma única conexão para várias chamadas de conexao_usuario()
dentro do bloco, em vez de abrir uma nova a cada chamada. Garante que:
(1) dentro do bloco, chamadas aninhadas reaproveitam a MESMA conexão;
(2) fora do bloco, nada muda — cada chamada continua abrindo a sua;
(3) o isolamento por RLS continua valendo igual dentro do bloco."""

from decimal import Decimal

from src import contas
from src.banco_de_dados import (
    conexao_usuario,
    definir_usuario_atual,
    transacao_compartilhada,
)


def test_fora_do_bloco_cada_chamada_abre_conexao_propria():
    with conexao_usuario() as conn1:
        pass
    with conexao_usuario() as conn2:
        pass
    assert conn1 is not conn2


def test_dentro_do_bloco_chamadas_aninhadas_reaproveitam_a_mesma_conexao():
    with transacao_compartilhada() as conn_compartilhada:
        with conexao_usuario() as conn1:
            assert conn1 is conn_compartilhada
        with conexao_usuario() as conn2:
            assert conn2 is conn_compartilhada
        assert conn1 is conn2


def test_apos_o_bloco_volta_ao_comportamento_normal():
    with transacao_compartilhada():
        pass
    with conexao_usuario() as conn_depois:
        pass
    # não deve mais ser a mesma conexão/transação do bloco compartilhado
    assert conn_depois is not None


def test_isolamento_rls_continua_valendo_dentro_do_bloco_compartilhado(
    usuario_a_id, usuario_b_id
):
    definir_usuario_atual(usuario_a_id)
    conta_a_id = contas.criar_conta("Conta Compartilhada A", "conta_corrente", None, Decimal("0"))
    try:
        definir_usuario_atual(usuario_b_id)
        with transacao_compartilhada():
            # mesmo reaproveitando conexão, B não pode ver a conta de A
            assert contas.obter_conta(conta_a_id) is None
            assert contas.listar_contas(incluir_inativas=True) == [] or all(
                c["id"] != conta_a_id for c in contas.listar_contas(incluir_inativas=True)
            )
    finally:
        definir_usuario_atual(usuario_a_id)
        contas.excluir_conta(conta_a_id)


def test_funcoes_de_negocio_reaproveitam_conexao_automaticamente(conta_a):
    """criar/obter/listar/excluir — tudo passa por conexao_usuario() sem
    saber que está (ou não) dentro de um bloco compartilhado."""
    with transacao_compartilhada():
        obtida = contas.obter_conta(conta_a)
        listadas = contas.listar_contas(incluir_inativas=True)
    assert obtida is not None
    assert any(c["id"] == conta_a for c in listadas)
