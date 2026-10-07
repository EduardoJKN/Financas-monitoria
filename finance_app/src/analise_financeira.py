"""Analytics financeiro pessoal, usado pela Visão Geral (Partes 13 a 21).

Toda função aqui opera exclusivamente no escopo do usuário autenticado: os
dados vêm de resumo_financeiro/transacoes, que já acessam o banco através de
conexao_usuario() (RLS) — nenhuma consulta aqui usa SQL bruto nem agrega
dados de outro usuário (ver Parte 25). Nenhum cálculo usa IA/machine
learning nem define um "score" arbitrário: tudo é determinístico, simples e
explicável a partir dos números do próprio usuário.
"""

from datetime import date, timedelta
from decimal import Decimal

from src import resumo_financeiro as resumo
from src import transacoes as transacoes_modulo
from src.datas import avancar_meses

DIAS_MINIMOS_PROJECAO_CONFIAVEL = 5
AMOSTRA_MINIMA_ANOMALIA = 5


def _periodo_mes(referencia: date) -> tuple[date, date]:
    """(primeiro dia, último dia) do mês de `referencia`."""
    inicio = referencia.replace(day=1)
    fim = avancar_meses(inicio, 1) - timedelta(days=1)
    return inicio, fim


# ---------------------------------------------------------------------
# Partes 14 e 15 — fontes de receita e despesas por categoria
# ---------------------------------------------------------------------
def _resumo_categorias_com_percentual(
    data_inicial: date, data_final: date, tipo: str
) -> list[dict]:
    linhas = resumo.resumir_por_categoria(data_inicial, data_final, tipo=tipo)
    total = sum((linha["total"] for linha in linhas), Decimal("0"))
    resultado = [
        {
            **linha,
            "percentual": (linha["total"] / total * Decimal("100")) if total > 0 else Decimal("0"),
        }
        for linha in linhas
    ]
    return sorted(resultado, key=lambda linha: linha["total"], reverse=True)


def receitas_por_categoria(data_inicial: date, data_final: date) -> list[dict]:
    """Ranking de categorias de receita no período: valor e percentual
    sobre o total de receitas (Parte 14 — "de onde vem meu dinheiro")."""
    return _resumo_categorias_com_percentual(data_inicial, data_final, "receita")


def despesas_por_categoria(data_inicial: date, data_final: date) -> list[dict]:
    """Ranking de categorias de despesa no período (Parte 15 — "para onde
    está indo meu dinheiro")."""
    return _resumo_categorias_com_percentual(data_inicial, data_final, "despesa")


def maior_fonte_receita(data_inicial: date, data_final: date) -> dict | None:
    linhas = receitas_por_categoria(data_inicial, data_final)
    return linhas[0] if linhas else None


def categoria_maior_gasto(data_inicial: date, data_final: date) -> dict | None:
    linhas = despesas_por_categoria(data_inicial, data_final)
    return linhas[0] if linhas else None


def concentracao_receita(data_inicial: date, data_final: date) -> Decimal | None:
    """Percentual das receitas concentrado em uma única categoria (quanto
    maior, menos diversificada é a renda). None sem receitas no período."""
    maior = maior_fonte_receita(data_inicial, data_final)
    return maior["percentual"] if maior else None


# ---------------------------------------------------------------------
# Parte 16 — comparação histórica por categoria
# ---------------------------------------------------------------------
def _total_categoria_periodo(categoria_id: int, tipo: str, inicio: date, fim: date) -> Decimal:
    for linha in resumo.resumir_por_categoria(inicio, fim, tipo=tipo):
        if linha["categoria_id"] == categoria_id:
            return linha["total"]
    return Decimal("0")


def comparar_categoria_historico(
    categoria_id: int, tipo: str, referencia: date | None = None
) -> dict:
    """Para uma categoria: valor deste mês, do mês passado, média dos
    últimos 3 meses (anteriores ao atual) e variação do mês atual vs essa
    média."""
    referencia = referencia or date.today()
    inicio_atual, _ = _periodo_mes(referencia)
    valor_atual = _total_categoria_periodo(categoria_id, tipo, inicio_atual, referencia)

    inicio_mes_passado = avancar_meses(inicio_atual, -1)
    inicio_passado, fim_passado = _periodo_mes(inicio_mes_passado)
    valor_mes_passado = _total_categoria_periodo(categoria_id, tipo, inicio_passado, fim_passado)

    valores_3_meses = []
    cursor = inicio_mes_passado
    for _ in range(3):
        ini, fim = _periodo_mes(cursor)
        valores_3_meses.append(_total_categoria_periodo(categoria_id, tipo, ini, fim))
        cursor = avancar_meses(cursor, -1)
    media_3_meses = sum(valores_3_meses, Decimal("0")) / Decimal(len(valores_3_meses))

    variacao_vs_media = None
    if media_3_meses > 0:
        variacao_vs_media = (valor_atual - media_3_meses) / media_3_meses * Decimal("100")

    return {
        "categoria_id": categoria_id,
        "este_mes": valor_atual,
        "mes_passado": valor_mes_passado,
        "media_3_meses": media_3_meses,
        "variacao_vs_media_percentual": variacao_vs_media,
    }


# ---------------------------------------------------------------------
# Parte 17 — tendências mensais
# ---------------------------------------------------------------------
def evolucao_mensal_categoria(
    categoria_id: int, tipo: str, meses: int = 4, referencia: date | None = None
) -> list[dict]:
    """Série mensal (mais antigo -> mais recente) do total da categoria nos
    últimos `meses` meses, incluindo o mês de `referencia`. Meses sem
    nenhum lançamento aparecem com valor 0 (nunca "faltando")."""
    referencia = referencia or date.today()
    inicio_mes_atual, _ = _periodo_mes(referencia)
    resultado = []
    cursor = inicio_mes_atual
    for _ in range(meses):
        ini, fim = _periodo_mes(cursor)
        fim_para_consulta = min(fim, referencia) if ini == inicio_mes_atual else fim
        valor = _total_categoria_periodo(categoria_id, tipo, ini, fim_para_consulta)
        resultado.append({"mes": ini, "valor": valor})
        cursor = avancar_meses(cursor, -1)
    return list(reversed(resultado))


def detectar_padrao_consecutivo(serie: list[Decimal], minimo_meses: int = 3) -> str | None:
    """'crescimento' se os últimos `minimo_meses` valores da série (ordem
    cronológica) subiram mês a mês; 'queda' se caíram; None sem padrão claro
    ou dados insuficientes (nunca assume tendência com amostra pequena)."""
    if len(serie) < minimo_meses:
        return None
    ultimos = serie[-minimo_meses:]
    if all(ultimos[i] < ultimos[i + 1] for i in range(len(ultimos) - 1)):
        return "crescimento"
    if all(ultimos[i] > ultimos[i + 1] for i in range(len(ultimos) - 1)):
        return "queda"
    return None


# ---------------------------------------------------------------------
# Parte 18 — taxa de economia
# ---------------------------------------------------------------------
def taxa_economia(receitas: Decimal, despesas: Decimal) -> Decimal | None:
    """(receitas - despesas) / receitas, em percentual. None quando não há
    receita no período (divisão por zero não faz sentido financeiro aqui)."""
    if receitas <= 0:
        return None
    return (receitas - despesas) / receitas * Decimal("100")


def taxa_economia_periodo(data_inicial: date, data_final: date) -> dict:
    resumo_periodo = resumo.calcular_resumo_periodo(data_inicial, data_final)
    return {
        "taxa": taxa_economia(resumo_periodo["total_receitas"], resumo_periodo["total_despesas"]),
        "receitas": resumo_periodo["total_receitas"],
        "despesas": resumo_periodo["total_despesas"],
    }


# ---------------------------------------------------------------------
# Parte 19 — projeção simples do mês (sem IA)
# ---------------------------------------------------------------------
def projetar_gasto_mes(referencia: date | None = None) -> dict:
    """Projeção = (despesas acumuladas / dias decorridos) * dias do mês.
    Transparente e simples de propósito — nunca usa IA. confianca_baixa
    fica True quando há poucos dias de dados ainda (evita projeção
    enganosa logo no início do mês)."""
    referencia = referencia or date.today()
    inicio_mes, fim_mes = _periodo_mes(referencia)
    dias_decorridos = (referencia - inicio_mes).days + 1
    dias_do_mes = (fim_mes - inicio_mes).days + 1

    despesas_acumuladas = resumo.calcular_resumo_periodo(inicio_mes, referencia)["total_despesas"]
    media_diaria = despesas_acumuladas / Decimal(dias_decorridos)
    projecao = (media_diaria * Decimal(dias_do_mes)).quantize(Decimal("0.01"))

    inicio_mes_passado = avancar_meses(inicio_mes, -1)
    inicio_passado, fim_passado = _periodo_mes(inicio_mes_passado)
    despesas_mes_passado = resumo.calcular_resumo_periodo(inicio_passado, fim_passado)[
        "total_despesas"
    ]

    valores_3_meses = []
    cursor = inicio_mes_passado
    for _ in range(3):
        ini, fim = _periodo_mes(cursor)
        valores_3_meses.append(resumo.calcular_resumo_periodo(ini, fim)["total_despesas"])
        cursor = avancar_meses(cursor, -1)
    media_3_meses = sum(valores_3_meses, Decimal("0")) / Decimal(len(valores_3_meses))

    return {
        "despesas_acumuladas": despesas_acumuladas,
        "dias_decorridos": dias_decorridos,
        "dias_do_mes": dias_do_mes,
        "projecao_fim_mes": projecao,
        "confianca_baixa": dias_decorridos < DIAS_MINIMOS_PROJECAO_CONFIAVEL,
        "mes_passado_total": despesas_mes_passado,
        "media_3_meses": media_3_meses,
    }


# ---------------------------------------------------------------------
# Parte 20 — insights determinísticos
# ---------------------------------------------------------------------
def _fmt_pct(valor: Decimal) -> str:
    return f"{valor:.1f}%".replace(".", ",")


def gerar_insights(referencia: date | None = None) -> list[str]:
    """Gera frases determinísticas, cada uma diretamente explicável pelos
    dados usados para calculá-la (nunca um score arbitrário)."""
    referencia = referencia or date.today()
    inicio_mes, _ = _periodo_mes(referencia)
    inicio_mes_passado = avancar_meses(inicio_mes, -1)
    inicio_passado, fim_passado = _periodo_mes(inicio_mes_passado)

    insights: list[str] = []

    taxa_atual = taxa_economia_periodo(inicio_mes, referencia)
    taxa_passada = taxa_economia_periodo(inicio_passado, fim_passado)
    if taxa_atual["taxa"] is not None and taxa_passada["taxa"] is not None:
        diferenca = taxa_atual["taxa"] - taxa_passada["taxa"]
        if diferenca > Decimal("1"):
            insights.append(
                f"Sua taxa de economia melhorou de {_fmt_pct(taxa_passada['taxa'])} "
                f"para {_fmt_pct(taxa_atual['taxa'])}."
            )
        elif diferenca < Decimal("-1"):
            insights.append(
                f"Sua taxa de economia caiu de {_fmt_pct(taxa_passada['taxa'])} "
                f"para {_fmt_pct(taxa_atual['taxa'])}."
            )

    concentracao = concentracao_receita(inicio_mes, referencia)
    if concentracao is not None and concentracao >= Decimal("60"):
        insights.append(f"{_fmt_pct(concentracao)} das suas receitas vêm de uma única categoria.")

    maior_gasto = categoria_maior_gasto(inicio_mes, referencia)
    if maior_gasto is not None:
        comparacao = comparar_categoria_historico(maior_gasto["categoria_id"], "despesa", referencia)
        variacao = comparacao["variacao_vs_media_percentual"]
        if variacao is not None and variacao >= Decimal("15"):
            insights.append(
                f"{maior_gasto['categoria']} está {_fmt_pct(variacao)} acima da média "
                "dos últimos três meses."
            )

    for linha in despesas_por_categoria(inicio_mes, referencia):
        serie = [
            item["valor"]
            for item in evolucao_mensal_categoria(
                linha["categoria_id"], "despesa", meses=4, referencia=referencia
            )
        ]
        padrao = detectar_padrao_consecutivo(serie)
        if padrao == "crescimento":
            insights.append(f"{linha['categoria']} aumentou pelo terceiro mês consecutivo.")
        elif padrao == "queda":
            insights.append(f"{linha['categoria']} caiu pelo terceiro mês consecutivo.")

    return insights


# ---------------------------------------------------------------------
# Parte 21 — detecção de gastos fora do padrão (estatística simples, IQR)
# ---------------------------------------------------------------------
def _percentil(valores_ordenados: list[Decimal], percentil: Decimal) -> Decimal:
    if not valores_ordenados:
        return Decimal("0")
    posicao = (percentil / Decimal("100")) * Decimal(len(valores_ordenados) - 1)
    indice_inferior = int(posicao)
    indice_superior = min(indice_inferior + 1, len(valores_ordenados) - 1)
    fracao = posicao - Decimal(indice_inferior)
    inferior = valores_ordenados[indice_inferior]
    superior = valores_ordenados[indice_superior]
    return inferior + (superior - inferior) * fracao


def detectar_lancamentos_fora_padrao(
    categoria_id: int, data_inicial: date, data_final: date
) -> list[dict]:
    """Lançamentos de despesa de uma categoria com valor muito maior que o
    normal para ela, usando a regra do IQR (limite = Q3 + 1.5 * IQR) —
    mais robusta a poucos outliers do que média/desvio padrão. Exige uma
    amostra mínima de AMOSTRA_MINIMA_ANOMALIA lançamentos; com menos que
    isso, retorna lista vazia (nunca marca anomalia sem base estatística
    suficiente)."""
    lancamentos = transacoes_modulo.listar_transacoes(
        tipo="despesa",
        categoria_id=categoria_id,
        data_inicial=data_inicial,
        data_final=data_final,
    )
    if len(lancamentos) < AMOSTRA_MINIMA_ANOMALIA:
        return []

    valores = sorted(lancamento["valor"] for lancamento in lancamentos)
    q1 = _percentil(valores, Decimal("25"))
    q3 = _percentil(valores, Decimal("75"))
    limite_superior = q3 + (q3 - q1) * Decimal("1.5")
    if limite_superior <= 0:
        return []

    return [l for l in lancamentos if l["valor"] > limite_superior]
