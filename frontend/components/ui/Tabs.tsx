"use client";

import { useState, ReactNode } from "react";

type Aba = {
  id: string;
  rotulo: string;
  conteudo: ReactNode;
};

/** Abas em desktop; em mobile, um seletor (select) — evita abas apertadas
 * demais em telas pequenas (Parte 15: "seletor apropriado em mobile"). */
export function Tabs({ abas, abaInicial }: { abas: Aba[]; abaInicial?: string }) {
  const [ativa, setAtiva] = useState(abaInicial ?? abas[0]?.id);
  const abaAtual = abas.find((a) => a.id === ativa) ?? abas[0];

  return (
    <div>
      <div className="mb-4 sm:hidden">
        <label htmlFor="seletor-aba" className="sr-only">
          Seção
        </label>
        <select
          id="seletor-aba"
          value={ativa}
          onChange={(e) => setAtiva(e.target.value)}
          className="w-full rounded-lg border border-borda bg-background px-3 py-2 text-sm text-foreground"
        >
          {abas.map((aba) => (
            <option key={aba.id} value={aba.id}>
              {aba.rotulo}
            </option>
          ))}
        </select>
      </div>

      <div
        role="tablist"
        aria-label="Seções"
        className="mb-4 hidden gap-1 border-b border-borda sm:flex"
      >
        {abas.map((aba) => (
          <button
            key={aba.id}
            role="tab"
            aria-selected={ativa === aba.id}
            onClick={() => setAtiva(aba.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors
              ${ativa === aba.id ? "border-primaria text-primaria" : "border-transparent text-muted hover:text-foreground"}`}
          >
            {aba.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel">{abaAtual?.conteudo}</div>
    </div>
  );
}
