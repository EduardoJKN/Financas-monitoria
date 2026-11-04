import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { Categoria } from "@/lib/api/types";

export function useCategorias() {
  return useQuery({
    queryKey: ["categorias"],
    queryFn: () => apiFetch<Categoria[]>("/api/v1/categorias", { params: { incluir_inativas: true } }),
  });
}

type CategoriaInput = { nome: string; tipo: string; categoria_pai_id?: number | null };

export function useCriarCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: CategoriaInput) =>
      apiFetch<Categoria>("/api/v1/categorias", { method: "POST", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categorias"] }),
  });
}

export function useAtualizarCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: Partial<CategoriaInput> & { ativa?: boolean } }) =>
      apiFetch<Categoria>(`/api/v1/categorias/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categorias"] }),
  });
}

export function useExcluirCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/v1/categorias/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categorias"] }),
  });
}
