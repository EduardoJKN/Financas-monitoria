"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

import { useSessao } from "@/hooks/useSessao";
import { ITENS_NAVEGACAO } from "./navegacao";
import { ThemeToggle } from "./ThemeToggle";

/** Sidebar desktop (Parte 12) — oculta em mobile (ver BottomNav). */
export function Sidebar() {
  const caminho = usePathname();
  const { usuario, sair } = useSessao();

  return (
    <aside className="hidden w-64 flex-col border-r border-borda bg-superficie p-4 lg:flex">
      <div className="mb-6 px-2">
        <span className="text-lg font-semibold text-foreground">💰 Economia UaU</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1" aria-label="Navegação principal">
        {ITENS_NAVEGACAO.map((item) => {
          const ativo = caminho?.startsWith(item.href);
          const Icone = item.icone;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={ativo ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
                ${ativo ? "bg-primaria text-primaria-foreground" : "text-foreground hover:bg-borda/40"}`}
            >
              <Icone size={18} />
              {item.rotulo}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 flex flex-col gap-2 border-t border-borda pt-4">
        <div className="flex items-center justify-between px-2">
          <span className="truncate text-xs text-muted" title={usuario?.email ?? ""}>
            {usuario?.email}
          </span>
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
    </aside>
  );
}
