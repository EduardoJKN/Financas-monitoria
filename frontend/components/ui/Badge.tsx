import { ReactNode } from "react";
import { ArrowLeftRight, ArrowDownCircle, ArrowUpCircle, Landmark } from "lucide-react";

export type TipoLancamento = "receita" | "despesa" | "transferencia" | "pagamento_fatura";

const CONFIGURACAO: Record<
  TipoLancamento,
  { fundo: string; texto: string; rotulo: string; Icone: typeof ArrowUpCircle }
> = {
  receita: { fundo: "bg-receita-fundo", texto: "text-receita-texto", rotulo: "Receita", Icone: ArrowUpCircle },
  despesa: { fundo: "bg-despesa-fundo", texto: "text-despesa-texto", rotulo: "Despesa", Icone: ArrowDownCircle },
  transferencia: {
    fundo: "bg-transferencia-fundo",
    texto: "text-transferencia-texto",
    rotulo: "Transferência",
    Icone: ArrowLeftRight,
  },
  pagamento_fatura: {
    fundo: "bg-fatura-fundo",
    texto: "text-fatura-texto",
    rotulo: "Pagamento de fatura",
    Icone: Landmark,
  },
};

/** Identificação visual por tipo — cor + ícone + texto sempre juntos, nunca
 * só a cor (acessibilidade para quem não distingue bem cores). */
export function BadgeTipo({ tipo }: { tipo: TipoLancamento }) {
  const config = CONFIGURACAO[tipo];
  const Icone = config.Icone;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.fundo} ${config.texto}`}
    >
      <Icone size={12} />
      {config.rotulo}
    </span>
  );
}

export function Badge({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-borda px-2.5 py-0.5 text-xs font-medium text-foreground ${className}`}
    >
      {children}
    </span>
  );
}
