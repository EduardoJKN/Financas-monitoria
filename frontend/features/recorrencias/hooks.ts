import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Recorrencia } from "@/lib/api/types";

export function useRecorrencias() {
  return useQuery({
    queryKey: ["recorrencias"],
    queryFn: () => apiFetch<Recorrencia[]>("/api/v1/recorrencias", { params: { incluir_inativas: true } }),
  });
}

type RecorrenciaInput = {
  tipo: string;
  descricao: string;
  valor: string;
  conta_id: number;
  periodicidade: string;
  data_inicio: string;
  categoria_id?: number | null;
  data_fim?: string | null;
};

function useInvalidarRecorrencias() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["recorrencias"] });
    queryClient.invalidateQueries({ queryKey: ["compromissos"] });
  };
}

export function useCriarRecorrencia() {
  const invalidar = useInvalidarRecorrencias();
  return useMutation({
    mutationFn: (dados: RecorrenciaInput) =>
      apiFetch<Recorrencia>("/api/v1/recorrencias", { method: "POST", body: dados }),
    onSuccess: invalidar,
  });
}

export function useAtualizarRecorrencia() {
  const invalidar = useInvalidarRecorrencias();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<RecorrenciaInput> & { ativa?: boolean } }) =>
      apiFetch<Recorrencia>(`/api/v1/recorrencias/${id}`, { method: "PATCH", body: dados }),
    onSuccess: invalidar,
  });
}

export function useExcluirRecorrencia() {
  const invalidar = useInvalidarRecorrencias();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/recorrencias/${id}`, { method: "DELETE" }),
    onSuccess: invalidar,
  });
}

export function useGerarPendentes() {
  const invalidar = useInvalidarRecorrencias();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ total_gerado: number; por_recorrencia: Record<string, number> }>(
        "/api/v1/recorrencias/gerar-pendentes",
        { method: "POST", body: {} }
      ),
    onSuccess: () => {
      invalidar();
      queryClient.invalidateQueries({ queryKey: ["transacoes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
