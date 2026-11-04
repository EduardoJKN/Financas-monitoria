"use client";

import Link from "next/link";
import { ArrowRightLeft, Info, Lightbulb, Plus, Upload } from "lucide-react";

import { BadgeTipo, type TipoLancamento } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { LoadingCards, LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Money } from "@/components/ui/Money";
import { useSessao } from "@/hooks/useSessao";
import { useResumoDashboard } from "@/features/dashboard/hooks";
import { useTransacoes } from "@/features/lancamentos/hooks";
import { corFundoLancamento } from "@/lib/utils/corLancamento";
import { formatarData, formatarPercentual } from "@/lib/utils/formatadores";

const QUANTIDADE_RECENTES = 5;
const QUANTIDADE_INSIGHTS_HOME = 2;

export default function PaginaInicio() {
  const { usuario } = useSessao();
  const { data: resumo, isLoading } = useResumoDashboard();
  const { data: recentes, isLoading: carregandoRecentes } = useTransacoes({
    limit: QUANTIDADE_RECENTES,
  });

  const primeiroNome = usuario?.email?.split("@")[0] ?? "";
  const proximaFatura = resumo?.cartoes.cartoes.find(
    (c) => (c as { fatura_atual?: unknown }).fatura_atual
  ) as { fatura_atual?: { saldo_devedor: string; data_vencimento: string } } | undefined;
  const insights = resumo?.insights_principais.slice(0, QUANTIDADE_INSIGHTS_HOME) ?? [];

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-foreground">Olá, {primeiroNome} 👋</h1>
      <p className="mb-6 text-sm text-muted">Aqui está o resumo rápido das suas finanças.</p>

      {isLoading || !resumo ? (
        <LoadingCards quantidade={4} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard rotulo="Saldo" valor={<Money valor={resumo.saldo_total} />} />
          <MetricCard
            rotulo="Resultado do mês"
            valor={<Money valor={resumo.resultado} />}
            variacaoPositiva={Number(resumo.resultado) >= 0}
          />
          <MetricCard
            rotulo="Taxa de economia"
            valor={formatarPercentual(resumo.taxa_economia)}
          />
          <MetricCard
            rotulo="Próxima fatura"
            valor={
              proximaFatura?.fatura_atual ? (
                <Money valor={proximaFatura.fatura_atual.saldo_devedor} />
              ) : (
                "—"
              )
            }
          />
        </div>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold text-muted">Atalhos</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Link
          href="/lancamentos?novo=receita"
          className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-4 text-sm font-medium text-receita-texto hover:bg-receita-fundo"
        >
          <Plus size={20} />
          Receita
        </Link>
        <Link
          href="/lancamentos?novo=despesa"
          className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-4 text-sm font-medium text-despesa-texto hover:bg-despesa-fundo"
        >
          <Plus size={20} />
          Despesa
        </Link>
        <Link
          href="/lancamentos?novo=transferencia"
          className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-4 text-sm font-medium text-transferencia-texto hover:bg-transferencia-fundo"
        >
          <ArrowRightLeft size={20} />
          Transferência
        </Link>
        <Link
          href="/importacao"
          className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-4 text-sm font-medium text-foreground hover:bg-borda/40"
        >
          <Upload size={20} />
          Importar extrato
        </Link>
      </div>

      <div className="mb-3 mt-8 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted">Últimos lançamentos</h2>
        <Link href="/lancamentos" className="text-sm font-medium text-primaria hover:underline">
          Ver todos
        </Link>
      </div>
      {carregandoRecentes ? (
        <LoadingSkeleton className="h-40" />
      ) : !recentes || recentes.length === 0 ? (
        <EmptyState titulo="Nenhum lançamento ainda." descricao="Use os atalhos acima para começar." />
      ) : (
        <div className="flex flex-col gap-2">
          {recentes.map((t) => (
            <div
              key={t.id}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${corFundoLancamento(t.tipo)}`}
            >
              <div className="flex min-w-0 items-center gap-3">
                <BadgeTipo tipo={t.tipo as TipoLancamento} />
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{t.descricao}</p>
                  <p className="text-xs text-muted">{formatarData(t.data_transacao)}</p>
                </div>
              </div>
              <Money valor={t.valor} className="shrink-0 font-medium" />
            </div>
          ))}
        </div>
      )}

      {insights.length > 0 && (
        <>
          <h2 className="mb-3 mt-8 text-sm font-semibold text-muted">Para você</h2>
          <div className="flex flex-col gap-2">
            {insights.map((texto, indice) => (
              <div
                key={indice}
                className="flex items-start gap-3 rounded-lg border border-borda p-3 text-sm text-foreground"
              >
                {indice === 0 ? (
                  <Lightbulb size={18} className="mt-0.5 shrink-0 text-primaria" />
                ) : (
                  <Info size={18} className="mt-0.5 shrink-0 text-transferencia-texto" />
                )}
                <span>{texto}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
