"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * Cliente Supabase para uso em componentes client-side. Só usa variáveis
 * NEXT_PUBLIC_* (publishable key) — nunca uma chave privada, que nunca
 * deve existir no frontend (Parte 37).
 */
export function criarClienteNavegador() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
  );
}
