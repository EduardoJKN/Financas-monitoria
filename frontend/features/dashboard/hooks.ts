import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api/client";
import type { CompromissoPrevisto, GastoForaPadrao, ResumoDashboard } from "@/lib/api/types";

export function useResumoDashboard() {
  return useQuery({
    queryKey: ["dashboard", "resumo"],
    queryFn: () => apiFetch<ResumoDashboard>("/api/v1/dashboard/resumo"),
  });
}

export function useInsightsDashboard() {
  return useQuery({
    queryKey: ["dashboard", "insights"],
    queryFn: () => apiFetch<{ insights: string[] }>("/api/v1/dashboard/insights"),
  });
}

export function useCategoriasDashboard(dataInicial: string, dataFinal: string) {
  return useQuery({
    queryKey: ["dashboard", "categorias", dataInicial, dataFinal],
    queryFn: () =>
      apiFetch<{ receitas: unknown[]; despesas: unknown[] }>("/api/v1/dashboard/categorias", {
        params: { data_inicial: dataInicial, data_final: dataFinal },
      }),
  });
}

export type TendenciaCategoria = {
  serie: Array<{ mes: string; valor: string }>;
  comparacao: {
    categoria_id: number;
    este_mes: string;
    mes_passado: string;
    media_3_meses: string;
    variacao_vs_media_percentual: string | null;
  };
  padrao: "crescimento" | "queda" | null;
};

export function useTendenciasDashboard(categoriaId: number | null, tipo: string, meses = 6) {
  return useQuery({
    queryKey: ["dashboard", "tendencias", categoriaId, tipo, meses],
    queryFn: () =>
      apiFetch<TendenciaCategoria>("/api/v1/dashboard/tendencias", {
        params: { categoria_id: categoriaId as number, tipo, meses },
      }),
    enabled: categoriaId !== null,
  });
}

export function useGastosForaPadrao() {
  return useQuery({
    queryKey: ["dashboard", "gastos-fora-padrao"],
    queryFn: () =>
      apiFetch<{ gastos: GastoForaPadrao[] }>("/api/v1/dashboard/gastos-fora-padrao"),
  });
}

export function useCompromissosPrevistos(meses = 4) {
  return useQuery({
    queryKey: ["compromissos", meses],
    queryFn: () =>
      apiFetch<{ compromissos: CompromissoPrevisto[] }>("/api/v1/compromissos/previstos", {
        params: { meses },
      }),
  });
}
