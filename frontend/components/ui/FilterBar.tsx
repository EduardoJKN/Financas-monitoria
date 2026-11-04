"use client";

import { ReactNode, useState } from "react";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

type Props = {
  children: ReactNode;
  contagemAtivos?: number;
};

/** Barra de filtros organizada no desktop; no mobile vira um botão que abre
 * uma folha (drawer) com os mesmos filtros, para não ocupar espaço de tela
 * útil numa viewport pequena. Os mesmos campos (children) são reaproveitados
 * nos dois formatos — nunca duplicar lógica de filtro por breakpoint. */
export function FilterBar({ children, contagemAtivos = 0 }: Props) {
  const [abertoMobile, setAbertoMobile] = useState(false);

  return (
    <>
      <div className="mb-4 hidden flex-wrap items-end gap-3 rounded-xl border border-borda bg-superficie p-3 sm:flex">
        {children}
      </div>

      <div className="mb-4 sm:hidden">
        <Button variante="secundaria" onClick={() => setAbertoMobile(true)} className="w-full">
          <SlidersHorizontal size={16} />
          Filtros
          {contagemAtivos > 0 && (
            <span className="ml-1 inline-flex min-w-5 items-center justify-center rounded-full bg-primaria px-1.5 py-0.5 text-xs text-primaria-foreground">
              {contagemAtivos}
            </span>
          )}
        </Button>
      </div>

      {abertoMobile && (
        <Modal aberto titulo="Filtros" onFechar={() => setAbertoMobile(false)}>
          <div className="flex flex-col gap-4">
            {children}
            <Button onClick={() => setAbertoMobile(false)}>Aplicar filtros</Button>
          </div>
        </Modal>
      )}
    </>
  );
}
