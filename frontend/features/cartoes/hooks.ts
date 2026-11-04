import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Cartao, Fatura } from "@/lib/api/types";

export function useCartoes() {
  return useQuery({
    queryKey: ["cartoes"],
    queryFn: () => apiFetch<Cartao[]>("/api/v1/cartoes", { params: { incluir_inativos: true } }),
  });
}

export function useFaturas(cartaoId: number | null) {
  return useQuery({
    queryKey: ["faturas", cartaoId],
    queryFn: () => apiFetch<Fatura[]>("/api/v1/faturas", { params: { cartao_id: cartaoId ?? undefined } }),
    enabled: cartaoId !== null,
  });
}

export function useCriarCartao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: {
      nome: string;
      limite: string;
      dia_fechamento: number;
      dia_vencimento: number;
      instituicao?: string | null;
      conta_pagamento_id?: number | null;
    }) => apiFetch<Cartao>("/api/v1/cartoes", { method: "POST", body: dados }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cartoes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useAtualizarCartao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      dados,
    }: {
      id: number;
      dados: Partial<{
        nome: string;
        limite: string;
        dia_fechamento: number;
        dia_vencimento: number;
        instituicao: string | null;
        conta_pagamento_id: number | null;
        ativo: boolean;
      }>;
    }) => apiFetch<Cartao>(`/api/v1/cartoes/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cartoes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function usePagarFatura() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      faturaId,
      dados,
    }: {
      faturaId: number;
      dados: { conta_id: number; valor: string; data_pagamento: string };
    }) => apiFetch(`/api/v1/faturas/${faturaId}/pagamentos`, { method: "POST", body: dados }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cartoes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
