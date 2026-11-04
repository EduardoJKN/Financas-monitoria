"use client";

import { useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { apiFetch } from "@/lib/api/client";
import { formatarMoeda } from "@/lib/utils/formatadores";
import { paraDecimalApi } from "@/lib/utils/numero";

export default function PaginaSimulador() {
  const [saldoInicial, setSaldoInicial] = useState("0");
  const [aporteMensal, setAporteMensal] = useState("500");
  const [meses, setMeses] = useState("12");
  const [resultado, setResultado] = useState<{ saldo_final: string; evolucao: Array<{ mes: number; saldo: string }> } | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function projetar() {
    setCarregando(true);
    const resposta = await apiFetch<typeof resultado>("/api/v1/simulador/projecao", {
      method: "POST",
      body: {
        saldo_inicial: paraDecimalApi(saldoInicial),
        aporte_mensal: paraDecimalApi(aporteMensal),
        meses: Number(meses),
      },
    });
    setResultado(resposta);
    setCarregando(false);
  }

  return (
    <div>
      <PageHeader titulo="Simulador" descricao="Projeção simples de saldo com aportes constantes, sem rendimento." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="flex flex-col gap-4">
          <Input rotulo="Saldo inicial (R$)" value={saldoInicial} onChange={(e) => setSaldoInicial(e.target.value)} />
          <Input rotulo="Aporte mensal (R$)" value={aporteMensal} onChange={(e) => setAporteMensal(e.target.value)} />
          <Input rotulo="Meses" type="number" min={1} value={meses} onChange={(e) => setMeses(e.target.value)} />
          <Button onClick={projetar} carregando={carregando}>
            Projetar
          </Button>
        </Card>

        {resultado && (
          <Card className="flex flex-col gap-4">
            <div>
              <p className="text-sm text-muted">Saldo final projetado</p>
              <Money valor={resultado.saldo_final} className="text-2xl font-semibold text-foreground" />
            </div>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={resultado.evolucao}>
                  <XAxis dataKey="mes" fontSize={12} />
                  <YAxis fontSize={12} tickFormatter={(v) => formatarMoeda(v)} width={80} />
                  <Tooltip formatter={(valor) => formatarMoeda(Number(valor))} />
                  <Line type="monotone" dataKey="saldo" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
