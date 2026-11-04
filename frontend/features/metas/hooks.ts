import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Meta } from "@/lib/api/types";

export function useMetas() {
  return useQuery({
    queryKey: ["metas"],
    queryFn: () => apiFetch<Meta[]>("/api/v1/metas"),
  });
}

type MetaInput = {
  nome: string;
  data_inicio: string;
  valor_alvo: string;
  valor_atual?: string;
  data_limite?: string | null;
};

export function useCriarMeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: MetaInput) => apiFetch<Meta>("/api/v1/metas", { method: "POST", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["metas"] }),
  });
}

export function useAtualizarMeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<MetaInput> }) =>
      apiFetch<Meta>(`/api/v1/metas/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["metas"] }),
  });
}

export function useExcluirMeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/metas/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["metas"] }),
  });
}
