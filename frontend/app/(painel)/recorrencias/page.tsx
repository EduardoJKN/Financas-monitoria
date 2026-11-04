"use client";

import { useState } from "react";
import { Plus, RefreshCw, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useCategorias } from "@/features/categorias/hooks";
import { useContas } from "@/features/contas/hooks";
import {
  useCriarRecorrencia,
  useExcluirRecorrencia,
  useGerarPendentes,
  useRecorrencias,
} from "@/features/recorrencias/hooks";
import type { Recorrencia } from "@/lib/api/types";
import { formatarData } from "@/lib/utils/formatadores";

const ROTULO_PERIODICIDADE: Record<string, string> = {
  mensal: "Mensal",
  semanal: "Semanal",
  anual: "Anual",
};

export default function PaginaRecorrencias() {
  const { data: recorrencias, isLoading } = useRecorrencias();
  const { data: contas } = useContas();
  const excluirRecorrencia = useExcluirRecorrencia();
  const gerarPendentes = useGerarPendentes();
  const [modalAberto, setModalAberto] = useState(false);
  const [excluindo, setExcluindo] = useState<Recorrencia | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);

  function nomeConta(id: number) {
    return contas?.find((c) => c.id === id)?.nome ?? `#${id}`;
  }

  async function gerar() {
    const resultado = await gerarPendentes.mutateAsync();
    setMensagem(
      resultado.total_gerado === 0
        ? "Nenhum lançamento pendente para gerar."
        : `${resultado.total_gerado} lançamento(s) gerado(s).`
    );
  }

  return (
    <div>
      <PageHeader
        titulo="Recorrências"
        descricao="Lançamentos que se repetem automaticamente (assinaturas, salário, aluguel)."
        acoes={
          <>
            <Button variante="secundaria" onClick={gerar} carregando={gerarPendentes.isPending}>
              <RefreshCw size={16} /> Gerar pendentes
            </Button>
            <Button onClick={() => setModalAberto(true)}>
              <Plus size={16} /> Nova recorrência
            </Button>
          </>
        }
      />

      {mensagem && <p className="mb-4 text-sm text-muted">{mensagem}</p>}

      {isLoading ? (
        <LoadingSkeleton className="h-48" />
      ) : !recorrencias || recorrencias.length === 0 ? (
        <EmptyState
          titulo="Nenhuma recorrência cadastrada ainda."
          descricao="Cadastre assinaturas, salário ou aluguel para gerar lançamentos automaticamente."
        />
      ) : (
        <div className="flex flex-col gap-2">
          {recorrencias.map((recorrencia) => (
            <div
              key={recorrencia.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-borda px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2 text-sm text-foreground">
                <span className="font-medium">{recorrencia.descricao}</span>
                <Money valor={recorrencia.valor} />
                <Badge>{ROTULO_PERIODICIDADE[recorrencia.periodicidade]}</Badge>
                <span className="text-muted">{nomeConta(recorrencia.conta_id)}</span>
                <span className="text-muted">desde {formatarData(recorrencia.data_inicio)}</span>
                {!recorrencia.ativa && <Badge>Inativa</Badge>}
              </div>
              <button
                aria-label="Excluir recorrência"
                onClick={() => setExcluindo(recorrencia)}
                className="rounded p-1 text-despesa-texto hover:bg-despesa-fundo"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {modalAberto && <ModalNovaRecorrencia onFechar={() => setModalAberto(false)} />}

      <ConfirmDialog
        aberto={!!excluindo}
        titulo="Excluir recorrência"
        mensagem={`Tem certeza que deseja excluir "${excluindo?.descricao}"? Lançamentos já gerados não são afetados.`}
        confirmando={excluirRecorrencia.isPending}
        onConfirmar={async () => {
          if (excluindo) await excluirRecorrencia.mutateAsync(excluindo.id);
          setExcluindo(null);
        }}
        onCancelar={() => setExcluindo(null)}
      />
    </div>
  );
}

function ModalNovaRecorrencia({ onFechar }: { onFechar: () => void }) {
  const { data: contas } = useContas(false);
  const { data: categorias } = useCategorias();
  const criarRecorrencia = useCriarRecorrencia();

  const [tipo, setTipo] = useState("despesa");
  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  const [contaId, setContaId] = useState<number | null>(null);
  const [categoriaId, setCategoriaId] = useState<number | null>(null);
  const [periodicidade, setPeriodicidade] = useState("mensal");
  const [dataInicio, setDataInicio] = useState("");

  async function confirmar() {
    if (!contaId || !dataInicio) return;
    await criarRecorrencia.mutateAsync({
      tipo,
      descricao,
      valor,
      conta_id: contaId,
      categoria_id: categoriaId,
      periodicidade,
      data_inicio: dataInicio,
    });
    onFechar();
  }

  return (
    <Modal aberto titulo="Nova recorrência" onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Select
          rotulo="Tipo"
          opcoes={[
            { valor: "despesa", rotulo: "Despesa" },
            { valor: "receita", rotulo: "Receita" },
          ]}
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
        />
        <Input rotulo="Descrição" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        <Input
          rotulo="Valor"
          type="number"
          step="0.01"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
        />
        <Select
          rotulo="Conta"
          opcoes={[
            { valor: "", rotulo: "Selecione..." },
            ...(contas ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome })),
          ]}
          value={contaId !== null ? String(contaId) : ""}
          onChange={(e) => setContaId(e.target.value ? Number(e.target.value) : null)}
        />
        <Select
          rotulo="Categoria (opcional)"
          opcoes={[
            { valor: "", rotulo: "Sem categoria" },
            ...(categorias ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome })),
          ]}
          value={categoriaId !== null ? String(categoriaId) : ""}
          onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
        />
        <Select
          rotulo="Periodicidade"
          opcoes={[
            { valor: "mensal", rotulo: "Mensal" },
            { valor: "semanal", rotulo: "Semanal" },
            { valor: "anual", rotulo: "Anual" },
          ]}
          value={periodicidade}
          onChange={(e) => setPeriodicidade(e.target.value)}
        />
        <Input
          rotulo="Data de início"
          type="date"
          value={dataInicio}
          onChange={(e) => setDataInicio(e.target.value)}
        />
        <Button
          onClick={confirmar}
          carregando={criarRecorrencia.isPending}
          disabled={!descricao || !valor || !contaId || !dataInicio}
        >
          Criar recorrência
        </Button>
      </div>
    </Modal>
  );
}
