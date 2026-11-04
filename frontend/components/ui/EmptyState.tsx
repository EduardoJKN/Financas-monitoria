import { ReactNode } from "react";

type Props = {
  titulo: string;
  descricao?: string;
  icone?: ReactNode;
  acao?: ReactNode;
};

export function EmptyState({ titulo, descricao, icone, acao }: Props) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-borda p-8 text-center">
      {icone && <div className="text-muted">{icone}</div>}
      <p className="font-medium text-foreground">{titulo}</p>
      {descricao && <p className="text-sm text-muted">{descricao}</p>}
      {acao}
    </div>
  );
}
