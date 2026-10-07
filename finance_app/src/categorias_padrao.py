"""Categorias padrão sugeridas para um usuário novo.

Só cria algo quando o usuário autenticado no contexto atual ainda não tem
NENHUMA categoria própria — nunca duplica, nunca força, e o usuário pode
editar ou excluir qualquer uma delas depois normalmente (são categorias
comuns, sem nenhum tratamento especial no banco)."""

from src import categorias

CATEGORIAS_PADRAO: tuple[tuple[str, str], ...] = (
    ("Alimentação", "despesa"),
    ("Moradia", "despesa"),
    ("Transporte", "despesa"),
    ("Saúde", "despesa"),
    ("Lazer", "despesa"),
    ("Educação", "despesa"),
    ("Receitas", "receita"),
    ("Outros", "ambos"),
)


def criar_categorias_padrao_se_necessario() -> int:
    """Cria as categorias padrão se o usuário atual ainda não tiver nenhuma
    categoria cadastrada. Retorna quantas foram criadas (0 se já havia
    alguma categoria, nesse caso nada é alterado)."""
    if categorias.listar_categorias(incluir_inativas=True):
        return 0

    for nome, tipo in CATEGORIAS_PADRAO:
        categorias.criar_categoria(nome=nome, tipo=tipo)
    return len(CATEGORIAS_PADRAO)
