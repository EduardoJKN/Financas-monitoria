"""Formatação e parsing de valores monetários no padrão brasileiro."""

from decimal import Decimal, InvalidOperation


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
