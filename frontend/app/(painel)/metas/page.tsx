"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { LoadingCards } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAtualizarMeta, useCriarMeta, useExcluirMeta, useMetas } from "@/features/metas/hooks";
import type { Meta } from "@/lib/api/types";
import { formatarData, formatarPercentual } from "@/lib/utils/formatadores";
import { paraDecimalApi } from "@/lib/utils/numero";

export default function PaginaMetas() {
  const { data: metas, isLoading } = useMetas();
  const excluirMeta = useExcluirMeta();
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState<Meta | null>(null);
  const [excluindo, setExcluindo] = useState<Meta | null>(null);

  return (
    <div>
      <PageHeader
        titulo="Metas"
        acoes={
          <Button onClick={() => setModalAberto(true)}>
            <Plus size={16} /> Nova meta
          </Button>
        }
      />

      {isLoading ? (
        <LoadingCards quantidade={3} />
      ) : !metas || metas.length === 0 ? (
        <EmptyState titulo="Nenhuma meta cadastrada ainda." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metas.map((meta) => (
            <Card key={meta.id} className="flex flex-col gap-2">
              <p className="font-medium text-foreground">{meta.nome}</p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-borda">
                <div
                  className="h-full rounded-full bg-primaria"
                  style={{ width: `${Math.min(Number(meta.progresso.percentual), 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-sm">
                <Money valor={meta.valor_atual} />
                <span className="text-muted">de</span>
                <Money valor={meta.valor_alvo} />
              </div>
              <p className="text-xs text-muted">{formatarPercentual(meta.progresso.percentual)} concluído</p>
              {meta.data_limite && (
                <p className="text-xs text-muted">Prazo: {formatarData(meta.data_limite)}</p>
              )}
              <div className="mt-1 flex gap-2">
                <Button variante="fantasma" onClick={() => setEditando(meta)}>
                  <Pencil size={14} /> Editar
                </Button>
                <button
                  aria-label="Excluir meta"
                  onClick={() => setExcluindo(meta)}
                  className="rounded p-1 text-despesa-texto hover:bg-despesa-fundo"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {modalAberto && <ModalMeta onFechar={() => setModalAberto(false)} />}

      {editando && <ModalMeta metaExistente={editando} onFechar={() => setEditando(null)} />}

      <ConfirmDialog
        aberto={!!excluindo}
        titulo="Excluir meta"
        mensagem={`Tem certeza que deseja excluir "${excluindo?.nome}"?`}
        confirmando={excluirMeta.isPending}
        onConfirmar={async () => {
          if (excluindo) await excluirMeta.mutateAsync(excluindo.id);
          setExcluindo(null);
        }}
        onCancelar={() => setExcluindo(null)}
      />
    </div>
  );
}

function ModalMeta({ metaExistente, onFechar }: { metaExistente?: Meta; onFechar: () => void }) {
  const criarMeta = useCriarMeta();
  const atualizarMeta = useAtualizarMeta();
  const editando = !!metaExistente;
  const salvando = editando ? atualizarMeta.isPending : criarMeta.isPending;

  const [nome, setNome] = useState(metaExistente?.nome ?? "");
  const [valorAlvo, setValorAlvo] = useState(metaExistente?.valor_alvo ?? "");
  const [valorAtual, setValorAtual] = useState(metaExistente?.valor_atual ?? "");
  const [dataInicio, setDataInicio] = useState(
    metaExistente?.data_inicio ?? new Date().toISOString().slice(0, 10)
  );
  const [dataLimite, setDataLimite] = useState(metaExistente?.data_limite ?? "");

  async function confirmar() {
    if (metaExistente) {
      await atualizarMeta.mutateAsync({
        id: metaExistente.id,
        dados: {
          nome,
          valor_alvo: paraDecimalApi(valorAlvo),
          valor_atual: paraDecimalApi(valorAtual),
          data_inicio: dataInicio,
          data_limite: dataLimite || null,
        },
      });
    } else {
      await criarMeta.mutateAsync({
        nome,
        data_inicio: dataInicio,
        valor_alvo: paraDecimalApi(valorAlvo),
        data_limite: dataLimite || null,
      });
    }
    onFechar();
  }

  return (
    <Modal aberto titulo={editando ? "Editar meta" : "Nova meta"} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
        <Input rotulo="Valor alvo (R$)" value={valorAlvo} onChange={(e) => setValorAlvo(e.target.value)} />
        {editando && (
          <Input
            rotulo="Valor atual (R$)"
            value={valorAtual}
            onChange={(e) => setValorAtual(e.target.value)}
          />
        )}
        <Input rotulo="Data de início" type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} />
        <Input rotulo="Prazo (opcional)" type="date" value={dataLimite} onChange={(e) => setDataLimite(e.target.value)} />
        <Button onClick={confirmar} carregando={salvando} disabled={!nome || !valorAlvo}>
          {editando ? "Salvar alterações" : "Criar meta"}
        </Button>
      </div>
    </Modal>
  );
}
