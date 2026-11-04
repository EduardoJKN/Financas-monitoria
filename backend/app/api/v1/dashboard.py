"""Dashboard agregado (Parte 5/6 da migração): reduz round-trips do
frontend consolidando o que antes exigiriam várias chamadas separadas em
um único /dashboard/resumo. Endpoints complementares (tendências,
categorias, insights) só para quando a página realmente precisa de dados
mais pesados (ex.: trocar a categoria selecionada na aba Tendências).

Cache curto por usuário (ver app/core/cache.py) em /resumo: evita
recalcular tudo a cada rerender do dashboard em poucos segundos, sem
nunca misturar dados entre usuários (chave sempre inclui usuario_id) e
sempre invalidado após qualquer mutação (criar/editar/excluir lançamento,
importar, pagar fatura, conciliar — ver os outros routers)."""

from datetime import date

from fastapi import APIRouter, Depends

from app.core import cache
from app.core.contexto_usuario import com_usuario
from app.core.security import obter_usuario_atual
from src import analise_financeira as af
from src import resumo_financeiro as resumo
from src.banco_de_dados import transacao_compartilhada

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

TOP_N_CATEGORIAS = 5
TOP_N_INSIGHTS = 5


@router.get("/resumo")
@com_usuario
def resumo_dashboard(usuario_id: str = Depends(obter_usuario_atual)):
    cacheado = cache.obter(usuario_id, "dashboard_resumo")
    if cacheado is not None:
        return cacheado

    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    # transacao_compartilhada(): este endpoint sozinho chama
    # conexao_usuario() mais de dez vezes por baixo dos panos (cada
    # função de resumo_financeiro/analise_financeira abre a sua). Medido
    # em produção: ~900ms de latência de rede por round-trip ao Postgres
    # neste ambiente — sem reaproveitar a conexão, só este endpoint
    # levava ~39s. Com o bloco abaixo, todas essas chamadas reaproveitam
    # UMA conexão/transação (somente leitura, sem efeito colateral).
    with transacao_compartilhada():
        resumo_periodo = resumo.calcular_resumo_periodo(inicio_mes, hoje)
        taxa = af.taxa_economia_periodo(inicio_mes, hoje)

        resultado = {
            "periodo": {"inicio": inicio_mes, "fim": hoje},
            "saldo_total": resumo.calcular_saldo_total(),
            "saldos_contas": resumo.calcular_saldos_contas(),
            "receitas": resumo_periodo["total_receitas"],
            "despesas": resumo_periodo["total_despesas"],
            "resultado": resumo_periodo["resultado"],
            "taxa_economia": taxa["taxa"],
            "cartoes": resumo.calcular_indicadores_cartoes(hoje),
            "projecao_mes": af.projetar_gasto_mes(hoje),
            "maiores_receitas": af.receitas_por_categoria(inicio_mes, hoje)[:TOP_N_CATEGORIAS],
            "maiores_despesas": af.despesas_por_categoria(inicio_mes, hoje)[:TOP_N_CATEGORIAS],
            "insights_principais": af.gerar_insights(hoje)[:TOP_N_INSIGHTS],
        }
    cache.definir(usuario_id, "dashboard_resumo", resultado)
    return resultado


@router.get("/categorias")
@com_usuario
def categorias_dashboard(
    data_inicial: date, data_final: date, usuario_id: str = Depends(obter_usuario_atual)
):
    return {
        "receitas": af.receitas_por_categoria(data_inicial, data_final),
        "despesas": af.despesas_por_categoria(data_inicial, data_final),
    }


@router.get("/tendencias")
@com_usuario
def tendencias_dashboard(
    categoria_id: int,
    tipo: str,
    meses: int = 6,
    usuario_id: str = Depends(obter_usuario_atual),
):
    meses = min(max(meses, 1), 24)
    serie = af.evolucao_mensal_categoria(categoria_id, tipo, meses=meses)
    comparacao = af.comparar_categoria_historico(categoria_id, tipo)
    padrao = af.detectar_padrao_consecutivo([item["valor"] for item in serie])
    return {"serie": serie, "comparacao": comparacao, "padrao": padrao}


@router.get("/insights")
@com_usuario
def insights_dashboard(usuario_id: str = Depends(obter_usuario_atual)):
    return {"insights": af.gerar_insights()}


@router.get("/gastos-fora-padrao")
@com_usuario
def gastos_fora_padrao_dashboard(usuario_id: str = Depends(obter_usuario_atual)):
    """Despesas do mês atual que fogem do padrão histórico da própria
    categoria (Parte 20) — endpoint complementar, fora do /resumo: varre
    todas as categorias com despesa no mês (uma consulta a mais por
    categoria), custo que só vale a pena pagar quando a aba correspondente
    da Visão Geral é realmente aberta."""
    cacheado = cache.obter(usuario_id, "dashboard_gastos_fora_padrao")
    if cacheado is not None:
        return cacheado

    with transacao_compartilhada():
        resultado = {"gastos": af.gastos_fora_padrao_do_mes()}
    cache.definir(usuario_id, "dashboard_gastos_fora_padrao", resultado)
    return resultado
