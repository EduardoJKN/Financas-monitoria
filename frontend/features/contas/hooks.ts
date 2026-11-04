import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Conta } from "@/lib/api/types";

export function useContas(incluirInativas = true) {
  return useQuery({
    queryKey: ["contas", { incluirInativas }],
    queryFn: () =>
      apiFetch<Conta[]>("/api/v1/contas", { params: { incluir_inativas: incluirInativas } }),
  });
}

type ContaInput = {
  nome: string;
  tipo: string;
  instituicao?: string | null;
  saldo_inicial?: string;
};

export function useCriarConta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: ContaInput) => apiFetch<Conta>("/api/v1/contas", { method: "POST", body: dados }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contas"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useAtualizarConta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<ContaInput> & { ativa?: boolean } }) =>
      apiFetch<Conta>(`/api/v1/contas/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contas"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useExcluirConta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/contas/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contas"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useConciliarConta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data_referencia,
      saldo_informado,
    }: {
      id: number;
      data_referencia: string;
      saldo_informado: string;
    }) =>
      apiFetch(`/api/v1/contas/${id}/conciliar`, {
        method: "POST",
        body: { data_referencia, saldo_informado },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contas"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
