import { ReactNode } from "react";

import { Card } from "./Card";

type Props = {
  rotulo: string;
  valor: ReactNode;
  variacao?: string;
  variacaoPositiva?: boolean;
  icone?: ReactNode;
};

export function MetricCard({ rotulo, valor, variacao, variacaoPositiva, icone }: Props) {
  return (
    <Card className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{rotulo}</span>
        {icone && <span className="text-muted">{icone}</span>}
      </div>
      <span className="text-2xl font-semibold text-foreground">{valor}</span>
      {variacao && (
        <span
          className={`text-xs font-medium ${
            variacaoPositiva ? "text-receita-texto" : "text-despesa-texto"
          }`}
        >
          {variacao}
        </span>
      )}
    </Card>
  );
}
