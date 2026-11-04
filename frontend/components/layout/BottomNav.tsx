"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, LogOut } from "lucide-react";

import { useSessao } from "@/hooks/useSessao";
import { Modal } from "@/components/ui/Modal";
import { ITENS_BOTTOM_NAV, ITENS_NAVEGACAO } from "./navegacao";
import { ThemeToggle } from "./ThemeToggle";

/** Navegação mobile (Parte 13): barra inferior com os itens mais usados +
 * menu "Mais" (drawer) para o restante — nunca uma sidebar gigante
 * espremida em telas pequenas. */
export function BottomNav() {
  const caminho = usePathname();
  const { usuario, sair } = useSessao();
  const [menuAberto, setMenuAberto] = useState(false);

  const itensRestantes = ITENS_NAVEGACAO.filter(
    (item) => !ITENS_BOTTOM_NAV.some((b) => b.href === item.href)
  );

  return (
    <>
      <nav
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-borda bg-superficie lg:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {ITENS_BOTTOM_NAV.map((item) => {
          const ativo = caminho?.startsWith(item.href);
          const Icone = item.icone;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={ativo ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium
                ${ativo ? "text-primaria" : "text-muted"}`}
            >
              <Icone size={20} />
              {item.rotulo}
            </Link>
          );
        })}
        <button
          onClick={() => setMenuAberto(true)}
          className="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium text-muted"
        >
          <Menu size={20} />
          Mais
        </button>
      </nav>

      <Modal aberto={menuAberto} titulo="Mais opções" onFechar={() => setMenuAberto(false)}>
        <div className="flex flex-col gap-1">
          {itensRestantes.map((item) => {
            const Icone = item.icone;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuAberto(false)}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-borda/40"
              >
                <Icone size={18} />
                {item.rotulo}
              </Link>
            );
          })}
          <div className="mt-2 flex items-center justify-between border-t border-borda pt-3">
            <span className="truncate text-xs text-muted">{usuario?.email}</span>
            <ThemeToggle />
          </div>
          <button
            onClick={sair}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-borda/40"
          >
            <LogOut size={18} />
            Sair
          </button>
        </div>
      </Modal>
    </>
  );
}
