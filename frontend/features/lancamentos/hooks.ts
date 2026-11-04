import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Transacao } from "@/lib/api/types";

export type FiltrosLancamentos = {
  tipo?: string;
  conta_id?: number;
  categoria_id?: number;
  data_inicial?: string;
  data_final?: string;
  texto_busca?: string;
  limit?: number;
  offset?: number;
};

export function useTransacoes(filtros: FiltrosLancamentos) {
  return useQuery({
    queryKey: ["transacoes", filtros],
    queryFn: () => apiFetch<Transacao[]>("/api/v1/transacoes", { params: filtros }),
  });
}

type TransacaoInput = {
  tipo: string;
  descricao: string;
  valor: string;
  data_transacao: string;
  conta_id?: number | null;
  cartao_id?: number | null;
  conta_destino_id?: number | null;
  categoria_id?: number | null;
  observacao?: string | null;
};

function useInvalidarTudo() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["transacoes"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["contas"] });
    queryClient.invalidateQueries({ queryKey: ["cartoes"] });
  };
}

export function useCriarTransacao() {
  const invalidar = useInvalidarTudo();
  return useMutation({
    mutationFn: (dados: TransacaoInput) =>
      apiFetch<Transacao>("/api/v1/transacoes", { method: "POST", body: dados }),
    onSuccess: invalidar,
  });
}

export function useAtualizarTransacao() {
  const invalidar = useInvalidarTudo();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<TransacaoInput> }) =>
      apiFetch<Transacao>(`/api/v1/transacoes/${id}`, { method: "PATCH", body: dados }),
    onSuccess: invalidar,
  });
}

export function useExcluirTransacao() {
  const invalidar = useInvalidarTudo();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/transacoes/${id}`, { method: "DELETE" }),
    onSuccess: invalidar,
  });
}

export function useCriarParcelamento() {
  const invalidar = useInvalidarTudo();
  return useMutation({
    mutationFn: (dados: {
      tipo: string;
      descricao: string;
      valor_total: string;
      data_primeira_parcela: string;
      total_parcelas: number;
      conta_id?: number | null;
      cartao_id?: number | null;
      categoria_id?: number | null;
    }) =>
      apiFetch<{ transacao_ids: number[] }>("/api/v1/transacoes/parcelamento", {
        method: "POST",
        body: dados,
      }),
    onSuccess: invalidar,
  });
}
