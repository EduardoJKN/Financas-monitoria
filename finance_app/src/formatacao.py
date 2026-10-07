"""Formatação e parsing de valores monetários no padrão brasileiro, e
identificação visual (badges e cor de linha) por tipo de lançamento."""

from decimal import Decimal, InvalidOperation

BADGES_TIPO_TRANSACAO = {
    "receita": "🟢 Receita",
    "despesa": "🔴 Despesa",
    "transferencia": "🔵 Transferência",
}

# Fundo suave (rgba com alfa baixo) para colorir a linha inteira de um
# lançamento. rgba (em vez de hex opaco) foi escolhido de propósito: o tom
# se mistura com a cor de fundo do tema (claro ou escuro) em vez de impor um
# fundo fixo, preservando legibilidade do texto em ambos os temas.
CORES_FUNDO_TIPO_LANCAMENTO = {
    "receita": "rgba(46, 204, 113, 0.16)",
    "despesa": "rgba(231, 76, 60, 0.16)",
    "transferencia": "rgba(52, 152, 219, 0.16)",
    "pagamento_fatura": "rgba(155, 89, 182, 0.18)",
}


def badge_tipo_transacao(tipo: str | None) -> str:
    """Rótulo com identificação visual (cor por emoji) do tipo de lançamento.

    Nunca levanta erro: tipos desconhecidos ou None caem em um rótulo neutro,
    em vez de quebrar a interface.
    """
    if tipo in BADGES_TIPO_TRANSACAO:
        return BADGES_TIPO_TRANSACAO[tipo]
    if not tipo:
        return "⚪ —"
    return f"⚪ {str(tipo).capitalize()}"


def badge_pagamento_fatura() -> str:
    """Identificação visual (roxo) para pagamento de fatura de cartão."""
    return "🟣 Pagamento de fatura"


def cor_fundo_lancamento(tipo: str | None) -> str | None:
    """Cor de fundo (rgba) para a linha de um lançamento, por tipo.

    tipo aceita 'receita', 'despesa', 'transferencia' ou 'pagamento_fatura'.
    Retorna None para tipos desconhecidos (nenhuma cor é aplicada nesse caso,
    em vez de levantar erro)."""
    return CORES_FUNDO_TIPO_LANCAMENTO.get(tipo)


def container_linha_colorida(st_module, chave: str, tipo: str | None):
    """Container do Streamlit com fundo colorido conforme o tipo de lançamento.

    Usa st.container(key=...) — API pública e estável do Streamlit — mais um
    bloco de CSS mínimo direcionado à classe `st-key-<chave>` que o próprio
    Streamlit atribui a esse container. Não depende de seletores internos
    não documentados (ex.: estrutura de divs gerada internamente), apenas da
    classe estável derivada da key, por isso é seguro reaproveitar entre
    páginas sem medo de quebrar em atualizações do Streamlit.

    `st_module` é o módulo `streamlit` importado pela página chamadora
    (passado explicitamente para manter este arquivo sem dependência direta
    do Streamlit, já que é usado também por testes puros).
    """
    cor = cor_fundo_lancamento(tipo)
    chave_css = "".join(c if c.isalnum() or c == "_" else "_" for c in chave)
    if cor:
        st_module.markdown(
            f"<style>.st-key-{chave_css} {{ background-color: {cor}; "
            "border-radius: 0.5rem; padding: 0.35rem 0.6rem; }}</style>",
            unsafe_allow_html=True,
        )
    return st_module.container(key=chave_css)


def formatar_moeda(valor: Decimal) -> str:
    """Formata um Decimal como moeda brasileira, ex.: Decimal('1234.56') -> 'R$ 1.234,56'."""
    sinal = "-" if valor < 0 else ""
    valor_absoluto = abs(valor)
    texto = f"{valor_absoluto:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sinal}R$ {texto}"


def texto_para_decimal(texto: str) -> Decimal:
    """Converte texto em Decimal, aceitando formatos comuns de extratos/formulários:

    - '1234.56'       (decimal internacional)
    - '1.234,56'      (decimal brasileiro, com milhar)
    - '-85,90'        (negativo)
    - 'R$ 1.234,56'   (com prefixo de moeda)
    - '(85,90)'       (negativo entre parênteses)

    Nunca constrói o Decimal a partir de float, apenas de texto, para evitar
    erros de arredondamento binário.
    """
    original = texto
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Informe um valor.")

    texto = texto.replace("R$", "").replace("r$", "").strip()
    texto = texto.replace(" ", "")

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1]
    if texto.startswith("-"):
        negativo = True
        texto = texto[1:]
    elif texto.startswith("+"):
        texto = texto[1:]

    if not texto:
        raise ValueError(f"Valor inválido: '{original}'.")

    pos_virgula = texto.rfind(",")
    pos_ponto = texto.rfind(".")

    if pos_virgula == -1 and pos_ponto == -1:
        normalizado = texto
    elif pos_virgula > pos_ponto:
        # vírgula é o separador decimal (formato brasileiro); pontos são milhar
        normalizado = texto.replace(".", "").replace(",", ".")
    else:
        # ponto é o separador decimal (formato internacional); vírgulas são milhar
        normalizado = texto.replace(",", "")

    try:
        valor = Decimal(normalizado)
    except InvalidOperation as exc:
        raise ValueError(
            f"Valor inválido: '{original}'. Use um número, por exemplo 1234,56."
        ) from exc

    return -valor if negativo else valor
