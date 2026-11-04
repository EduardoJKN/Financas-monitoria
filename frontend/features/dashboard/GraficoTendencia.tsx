"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatarMes, formatarMoeda } from "@/lib/utils/formatadores";

export function GraficoTendencia({
  serie,
  cor,
}: {
  serie: Array<{ mes: string; valor: string }>;
  cor: string;
}) {
  const dados = serie.map((item) => ({ ...item, rotulo: formatarMes(item.mes) }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dados} margin={{ left: 8, right: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="rotulo" fontSize={12} />
          <YAxis tickFormatter={(v) => formatarMoeda(v)} fontSize={12} width={90} />
          <Tooltip formatter={(valor) => formatarMoeda(Number(valor))} />
          <Line type="monotone" dataKey="valor" stroke={cor} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
