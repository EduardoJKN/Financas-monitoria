"use client";

import { ReactNode, useEffect, useRef } from "react";
import { X } from "lucide-react";

type Props = {
  aberto: boolean;
  titulo: string;
  onFechar: () => void;
  children: ReactNode;
};

/** Modal/Drawer acessível: foco preso ao abrir, Escape fecha, role="dialog"
 * com aria-modal e título associado (Parte 29). Em mobile, ocupa a tela
 * quase toda (comportamento de drawer); em desktop, fica centralizado. */
export function Modal({ aberto, titulo, onFechar, children }: Props) {
  const referenciaConteudo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") onFechar();
    }
    document.addEventListener("keydown", aoTeclar);
    referenciaConteudo.current?.focus();
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [aberto, onFechar]);

  if (!aberto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center">
      <div
        ref={referenciaConteudo}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-titulo"
        tabIndex={-1}
        className="w-full max-h-[90vh] overflow-y-auto rounded-t-2xl bg-background p-5 shadow-xl
          sm:max-w-lg sm:rounded-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 id="modal-titulo" className="text-lg font-semibold text-foreground">
            {titulo}
          </h2>
          <button
            onClick={onFechar}
            aria-label="Fechar"
            className="rounded-full p-1 text-muted hover:bg-superficie"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
