import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Regra } from "@/lib/api/types";

export function useRegras() {
  return useQuery({
    queryKey: ["regras"],
    queryFn: () => apiFetch<Regra[]>("/api/v1/regras", { params: { incluir_inativas: true } }),
  });
}

type RegraInput = {
  texto_busca: string;
  operador: string;
  categoria_id: number;
  prioridade?: number;
};

export function useCriarRegra() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: RegraInput) => apiFetch<Regra>("/api/v1/regras", { method: "POST", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regras"] }),
  });
}

export function useAtualizarRegra() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<RegraInput> & { ativa?: boolean } }) =>
      apiFetch<Regra>(`/api/v1/regras/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regras"] }),
  });
}

export function useExcluirRegra() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/regras/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regras"] }),
  });
}

export function usePreVisualizarRegra(regraId: number | null) {
  return useQuery({
    queryKey: ["regras", regraId, "pre-visualizar"],
    queryFn: () =>
      apiFetch<Array<{ id: number; descricao: string; valor: string; data_transacao: string }>>(
        `/api/v1/regras/${regraId}/pre-visualizar`
      ),
    enabled: regraId !== null,
  });
}

export function useAplicarRegra() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, transacaoIds }: { id: number; transacaoIds: number[] }) =>
      apiFetch<{ total_aplicado: number }>(`/api/v1/regras/${id}/aplicar`, {
        method: "POST",
        body: { transacao_ids: transacaoIds, somente_sem_categoria: true },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transacoes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
