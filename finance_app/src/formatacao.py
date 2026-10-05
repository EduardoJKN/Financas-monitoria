"""Formatação e parsing de valores monetários no padrão brasileiro."""

from decimal import Decimal, InvalidOperation


def formatar_moeda(valor: Decimal) -> str:
    """Formata um Decimal como moeda brasileira, ex.: Decimal('1234.56') -> 'R$ 1.234,56'."""
    sinal = "-" if valor < 0 else ""
    valor_absoluto = abs(valor)
    texto = f"{valor_absoluto:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sinal}R$ {texto}"


def texto_para_decimal(texto: str) -> Decimal:
    """Converte texto de formulário (ex.: '1.234,56' ou '1234.56') para Decimal."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Informe um valor.")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(
            f"Valor inválido: '{texto}'. Use um número, por exemplo 1234,56."
        ) from exc
