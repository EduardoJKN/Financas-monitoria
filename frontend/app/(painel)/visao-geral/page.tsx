"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Info, TrendingDown, TrendingUp } from "lucide-react";

import { formatarData, formatarMoeda } from "@/lib/utils/formatadores";

import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingCards, LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Tabs } from "@/components/ui/Tabs";
import { useCategorias } from "@/features/categorias/hooks";
import {
  useGastosForaPadrao,
  useResumoDashboard,
  useTendenciasDashboard,
} from "@/features/dashboard/hooks";
import { GraficoTendencia } from "@/features/dashboard/GraficoTendencia";
import { RankingCategorias } from "@/features/dashboard/RankingCategorias";
import { formatarPercentual } from "@/lib/utils/formatadores";

function classificarInsight(texto: string): "positivo" | "atencao" | "info" {
  const normalizado = texto.toLowerCase();
  if (normalizado.includes("melhorou") || normalizado.includes("caiu")) return "positivo";
  if (
    normalizado.includes("acima") ||
    normalizado.includes("aumentou") ||
    normalizado.includes("concentr")
  ) {
    return "atencao";
  }
  return "info";
}

const ICONE_INSIGHT = {
  positivo: <CheckCircle2 size={18} className="text-receita-texto" />,
  atencao: <AlertTriangle size={18} className="text-despesa-texto" />,
  info: <Info size={18} className="text-transferencia-texto" />,
};

export default function PaginaVisaoGeral() {
  const { data: resumo, isLoading } = useResumoDashboard();

  if (isLoading || !resumo) {
    return (
      <div>
        <PageHeader titulo="Visão Geral" />
        <LoadingCards quantidade={4} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader titulo="Visão Geral" descricao="Resumo, categorias, tendências e insights." />

      <Tabs
        abaInicial="resumo"
        abas={[
          {
            id: "resumo",
            rotulo: "Resumo",
            conteudo: (
              <div className="flex flex-col gap-6">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <MetricCard rotulo="Saldo total" valor={<Money valor={resumo.saldo_total} />} />
                  <MetricCard
                    rotulo="Receitas do período"
                    valor={<Money valor={resumo.receitas} />}
                  />
                  <MetricCard
                    rotulo="Despesas do período"
                    valor={<Money valor={resumo.despesas} />}
                  />
                  <MetricCard
                    rotulo="Resultado"
                    valor={<Money valor={resumo.resultado} />}
                    variacaoPositiva={Number(resumo.resultado) >= 0}
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <MetricCard
                    rotulo="Taxa de economia"
                    valor={formatarPercentual(resumo.taxa_economia)}
                  />
                  <MetricCard
                    rotulo={
                      resumo.projecao_mes.confianca_baixa
                        ? "Projeção do mês (baixa confiança)"
                        : "Projeção do mês"
                    }
                    valor={<Money valor={resumo.projecao_mes.projecao_fim_mes} />}
                  />
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-semibold text-muted">Saldos por conta</h3>
                  {resumo.saldos_contas.length === 0 ? (
                    <EmptyState titulo="Nenhuma conta cadastrada ainda." />
                  ) : (
                    <div className="flex flex-col gap-2">
                      {resumo.saldos_contas.map((conta) => (
                        <div
                          key={conta.conta_id}
                          className="flex items-center justify-between rounded-lg border border-borda px-3 py-2 text-sm"
                        >
                          <span>{conta.nome}</span>
                          <Money valor={conta.saldo} className="font-medium" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ),
          },
          {
            id: "categorias",
            rotulo: "Categorias",
            conteudo: (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-muted">Maiores receitas</h3>
                  <RankingCategorias dados={resumo.maiores_receitas} cor="#16a34a" />
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-muted">Maiores despesas</h3>
                  <RankingCategorias dados={resumo.maiores_despesas} cor="#dc2626" />
                </div>
              </div>
            ),
          },
          {
            id: "tendencias",
            rotulo: "Tendências",
            conteudo: <AbaTendencias />,
          },
          {
            id: "insights",
            rotulo: "Insights",
            conteudo: (
              <div className="flex flex-col gap-6">
                {resumo.insights_principais.length === 0 ? (
                  <EmptyState titulo="Nenhum insight relevante com os dados atuais." />
                ) : (
                  <div className="flex flex-col gap-2">
                    {resumo.insights_principais.map((texto, indice) => {
                      const tipo = classificarInsight(texto);
                      return (
                        <div
                          key={indice}
                          className="flex items-start gap-3 rounded-lg border border-borda p-3 text-sm"
                        >
                          {ICONE_INSIGHT[tipo]}
                          <span className="text-foreground">{texto}</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                <GastosForaPadrao />
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}

const ROTULO_PADRAO: Record<string, { texto: string; icone: typeof TrendingUp }> = {
  crescimento: { texto: "Em crescimento nos últimos meses", icone: TrendingUp },
  queda: { texto: "Em queda nos últimos meses", icone: TrendingDown },
};

function AbaTendencias() {
  const { data: categorias } = useCategorias();
  const [categoriaId, setCategoriaId] = useState<number | null>(null);
  const [tipo, setTipo] = useState("despesa");
  const { data: tendencia, isLoading } = useTendenciasDashboard(categoriaId, tipo);

  const categoriasDoTipo = (categorias ?? []).filter((c) => c.tipo === tipo || c.tipo === "ambos");

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
          rotulo="Tipo"
          opcoes={[
            { valor: "despesa", rotulo: "Despesa" },
            { valor: "receita", rotulo: "Receita" },
          ]}
          value={tipo}
          onChange={(e) => {
            setTipo(e.target.value);
            setCategoriaId(null);
          }}
        />
        <Select
          rotulo="Categoria"
          opcoes={[
            { valor: "", rotulo: "Selecione uma categoria..." },
            ...categoriasDoTipo.map((c) => ({ valor: String(c.id), rotulo: c.nome })),
          ]}
          value={categoriaId !== null ? String(categoriaId) : ""}
          onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
        />
      </div>

      {categoriaId === null ? (
        <EmptyState titulo="Selecione uma categoria para ver a evolução mensal e comparação com o histórico." />
      ) : isLoading || !tendencia ? (
        <LoadingSkeleton className="h-64" />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MetricCard rotulo="Este mês" valor={<Money valor={tendencia.comparacao.este_mes} />} />
            <MetricCard
              rotulo="Mês passado"
              valor={<Money valor={tendencia.comparacao.mes_passado} />}
            />
            <MetricCard
              rotulo="Média últimos 3 meses"
              valor={<Money valor={tendencia.comparacao.media_3_meses} />}
              variacao={
                tendencia.comparacao.variacao_vs_media_percentual
                  ? `${formatarPercentual(tendencia.comparacao.variacao_vs_media_percentual)} vs. média`
                  : undefined
              }
              variacaoPositiva={
                tipo === "receita"
                  ? Number(tendencia.comparacao.variacao_vs_media_percentual) >= 0
                  : Number(tendencia.comparacao.variacao_vs_media_percentual) <= 0
              }
            />
          </div>

          {tendencia.padrao && (
            <div className="flex items-center gap-2 rounded-lg border border-borda p-3 text-sm text-foreground">
              {(() => {
                const Icone = ROTULO_PADRAO[tendencia.padrao].icone;
                return <Icone size={18} className="text-muted" />;
              })()}
              {ROTULO_PADRAO[tendencia.padrao].texto}
            </div>
          )}

          <GraficoTendencia serie={tendencia.serie} cor={tipo === "receita" ? "#16a34a" : "#dc2626"} />
        </>
      )}
    </div>
  );
}

/** Parte 20 — "Gastos fora do padrão": despesas do mês que fogem do normal
 * histórico da própria categoria (regra IQR, calculada em
 * analise_financeira.py — nada recalculado aqui). Só aparece quando há
 * amostra suficiente; "não é alarme, é contexto". */
function GastosForaPadrao() {
  const { data, isLoading } = useGastosForaPadrao();

  if (isLoading) return <LoadingSkeleton className="h-24" />;
  const gastos = data?.gastos ?? [];
  if (gastos.length === 0) return null;

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-muted">Gastos fora do padrão</h3>
      <div className="flex flex-col gap-2">
        {gastos.map((g) => (
          <div
            key={g.transacao_id}
            className="flex items-start gap-3 rounded-lg border border-despesa-texto/30 bg-despesa-fundo p-3 text-sm"
          >
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-despesa-texto" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate font-medium text-foreground">
                  {g.categoria} · {g.descricao}
                </p>
                <Money valor={g.valor} className="shrink-0 font-semibold text-despesa-texto" />
              </div>
              <p className="text-xs text-muted">
                {formatarData(g.data_transacao)} — normalmente os gastos nesta categoria ficam
                entre {formatarMoeda(g.faixa_normal_min)} e {formatarMoeda(g.faixa_normal_max)}.
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
