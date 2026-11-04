"use client";

import { useState } from "react";

import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useCompromissosPrevistos } from "@/features/dashboard/hooks";
import { formatarMes } from "@/lib/utils/formatadores";

export default function PaginaCompromissos() {
  const [meses, setMeses] = useState(4);
  const { data, isLoading } = useCompromissosPrevistos(meses);

  return (
    <div>
      <PageHeader
        titulo="Compromissos previstos"
        descricao="Soma do que já está efetivamente comprometido: parcelas já lançadas, recorrências ativas e faturas de cartão existentes. Não é uma previsão garantida de gastos futuros ainda não realizados."
        acoes={
          <Select
            rotulo="Período"
            opcoes={[
              { valor: "3", rotulo: "3 meses" },
              { valor: "4", rotulo: "4 meses" },
              { valor: "6", rotulo: "6 meses" },
              { valor: "12", rotulo: "12 meses" },
            ]}
            value={String(meses)}
            onChange={(e) => setMeses(Number(e.target.value))}
          />
        }
      />

      {isLoading || !data ? (
        <LoadingSkeleton className="h-64" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.compromissos.map((compromisso) => (
            <Card key={compromisso.mes} className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold capitalize text-foreground">
                {formatarMes(compromisso.mes)}
              </h3>
              <div className="flex flex-col gap-1 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted">Parcelas já lançadas</span>
                  <Money valor={compromisso.parcelas_previstas} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Recorrências ativas</span>
                  <Money valor={compromisso.recorrencias_previstas} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Faturas conhecidas</span>
                  <Money valor={compromisso.faturas_conhecidas} />
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-borda pt-2 text-sm font-semibold">
                <span className="text-foreground">Total previsto</span>
                <Money valor={compromisso.total_previsto} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
