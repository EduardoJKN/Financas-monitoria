"use client";

import { Moon, Sun } from "lucide-react";

import { useTema } from "@/hooks/useTema";

export function ThemeToggle() {
  const { tema, alternar } = useTema();
  return (
    <button
      onClick={alternar}
      aria-label={tema === "escuro" ? "Mudar para tema claro" : "Mudar para tema escuro"}
      className="rounded-full p-1.5 text-muted hover:bg-borda/40"
    >
      {tema === "escuro" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
