"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/** TanStack Query (Parte 10): cache do cliente, invalidação após mutação,
 * loading/refetch padronizados. staleTime curto por padrão — dados
 * financeiros não devem parecer "desatualizados" por muito tempo. */
export function ProvedorQuery({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
