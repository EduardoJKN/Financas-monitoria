"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/ui/EmptyState";
import type { CategoriaResumo } from "@/lib/api/types";
import { formatarMoeda } from "@/lib/utils/formatadores";

const TOP_N = 8;

/** Ranking horizontal com Top N + "Outros" (Partes 15/23) — nunca uma
 * lista de dezenas de categorias ilegível. */
export function RankingCategorias({
  dados,
  cor,
}: {
  dados: CategoriaResumo[];
  cor: string;
}) {
  if (dados.length === 0) {
    return <EmptyState titulo="Sem dados no período selecionado." />;
  }

  const principais = dados.slice(0, TOP_N);
  const resto = dados.slice(TOP_N);
  const dadosGrafico = [...principais];
  if (resto.length > 0) {
    const somaResto = resto.reduce((acc, item) => acc + Number(item.total), 0);
    dadosGrafico.push({
      categoria_id: -1,
      categoria: "Outros",
      tipo: principais[0]?.tipo ?? "",
      total: String(somaResto),
      percentual: String(resto.reduce((acc, item) => acc + Number(item.percentual), 0)),
    });
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dadosGrafico} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => formatarMoeda(v)} fontSize={12} />
          <YAxis type="category" dataKey="categoria" width={110} fontSize={12} />
          <Tooltip formatter={(valor) => formatarMoeda(Number(valor))} />
          <Bar dataKey="total" radius={4}>
            {dadosGrafico.map((entrada) => (
              <Cell key={entrada.categoria_id} fill={cor} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
