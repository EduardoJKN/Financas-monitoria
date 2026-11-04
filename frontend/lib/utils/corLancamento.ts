import type { TipoLancamento } from "@/components/ui/Badge";

/** Classe de fundo para colorir a linha/card inteiro de um lançamento —
 * mesmo padrão de cores do Streamlit (verde/vermelho/azul/roxo suaves),
 * paridade visual entre as duas interfaces (Parte 17). */
export function corFundoLancamento(tipo: TipoLancamento | string | null | undefined): string {
  switch (tipo) {
    case "receita":
      return "bg-receita-fundo";
    case "despesa":
      return "bg-despesa-fundo";
    case "transferencia":
      return "bg-transferencia-fundo";
    case "pagamento_fatura":
      return "bg-fatura-fundo";
    default:
      return "";
  }
}
