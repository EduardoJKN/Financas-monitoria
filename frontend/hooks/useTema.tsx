"use client";

import { useCallback, useState } from "react";

type Tema = "claro" | "escuro";

function temaAtual(): Tema {
  if (typeof document === "undefined") return "claro";
  return document.documentElement.classList.contains("dark") ? "escuro" : "claro";
}

/** Alterna entre tema claro/escuro, persistindo a escolha (Parte 25).
 * A aplicação inicial (sem flash) é feita por <ThemeScript> no <head>,
 * síncrona e antes da hidratação — por isso o estado inicial aqui pode
 * ser lido direto do DOM (lazy initializer), sem precisar de useEffect. */
export function useTema() {
  const [tema, setTema] = useState<Tema>(() => temaAtual());

  const alternar = useCallback(() => {
    const novo: Tema = temaAtual() === "escuro" ? "claro" : "escuro";
    document.documentElement.classList.toggle("dark", novo === "escuro");
    document.documentElement.classList.toggle("light", novo === "claro");
    localStorage.setItem("tema", novo);
    setTema(novo);
  }, []);

  return { tema, alternar };
}
