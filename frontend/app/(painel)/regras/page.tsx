"use client";

import { useState } from "react";
import { Plus, Trash2, Wand2 } from "lucide-react";

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
import {
  useAplicarRegra,
  useAtualizarRegra,
  useCriarRegra,
  useExcluirRegra,
  usePreVisualizarRegra,
  useRegras,
} from "@/features/regras/hooks";
import type { Regra } from "@/lib/api/types";
import { formatarData } from "@/lib/utils/formatadores";

const ROTULO_OPERADOR: Record<string, string> = {
  contem: "contém",
  comeca_com: "começa com",
  igual: "é igual a",
};

export default function PaginaRegras() {
  const { data: regras, isLoading } = useRegras();
  const { data: categorias } = useCategorias();
  const excluirRegra = useExcluirRegra();
  const atualizarRegra = useAtualizarRegra();
  const [modalAberto, setModalAberto] = useState(false);
  const [excluindo, setExcluindo] = useState<Regra | null>(null);
  const [aplicando, setAplicando] = useState<Regra | null>(null);

  function caminhoCategoria(id: number) {
    const categoria = categorias?.find((c) => c.id === id);
    if (!categoria) return `#${id}`;
    if (categoria.categoria_pai_id) {
      const pai = categorias?.find((c) => c.id === categoria.categoria_pai_id);
      if (pai) return `${pai.nome} > ${categoria.nome}`;
    }
    return categoria.nome;
  }

  return (
    <div>
      <PageHeader
        titulo="Regras de categorização"
        descricao="Categorize automaticamente novos lançamentos a partir do texto da descrição."
        acoes={
          <Button onClick={() => setModalAberto(true)}>
            <Plus size={16} /> Nova regra
          </Button>
        }
      />

      {isLoading ? (
        <LoadingSkeleton className="h-48" />
      ) : !regras || regras.length === 0 ? (
        <EmptyState
          titulo="Nenhuma regra cadastrada ainda."
          descricao="Crie regras para categorizar automaticamente lançamentos importados ou futuros."
        />
      ) : (
        <div className="flex flex-col gap-2">
          {regras.map((regra) => (
            <div
              key={regra.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-borda px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2 text-sm text-foreground">
                <span>
                  Se descrição <strong>{ROTULO_OPERADOR[regra.operador]}</strong> &quot;{regra.texto_busca}&quot;
                </span>
                <span className="text-muted">→</span>
                <Badge>{caminhoCategoria(regra.categoria_id)}</Badge>
                <span className="text-xs text-muted">Prioridade {regra.prioridade}</span>
                {!regra.ativa && <Badge>Inativa</Badge>}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variante="fantasma"
                  onClick={() => atualizarRegra.mutate({ id: regra.id, dados: { ativa: !regra.ativa } })}
                >
                  {regra.ativa ? "Desativar" : "Ativar"}
                </Button>
                <Button
                  variante="fantasma"
                  onClick={() => setAplicando(regra)}
                  title="Revisar correspondências e aplicar ao histórico"
                >
                  <Wand2 size={16} /> Revisar e aplicar
                </Button>
                <button
                  aria-label="Excluir regra"
                  onClick={() => setExcluindo(regra)}
                  className="rounded p-1 text-despesa-texto hover:bg-despesa-fundo"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalAberto && <ModalNovaRegra onFechar={() => setModalAberto(false)} />}

      {aplicando && <ModalAplicarRegra regra={aplicando} onFechar={() => setAplicando(null)} />}

      <ConfirmDialog
        aberto={!!excluindo}
        titulo="Excluir regra"
        mensagem={`Tem certeza que deseja excluir esta regra de categorização?`}
        confirmando={excluirRegra.isPending}
        onConfirmar={async () => {
          if (excluindo) await excluirRegra.mutateAsync(excluindo.id);
          setExcluindo(null);
        }}
        onCancelar={() => setExcluindo(null)}
      />
    </div>
  );
}

function ModalNovaRegra({ onFechar }: { onFechar: () => void }) {
  const { data: categorias } = useCategorias();
  const criarRegra = useCriarRegra();
  const [textoBusca, setTextoBusca] = useState("");
  const [operador, setOperador] = useState("contem");
  const [categoriaId, setCategoriaId] = useState<number | null>(null);
  const [prioridade, setPrioridade] = useState("0");

  async function confirmar() {
    if (!categoriaId) return;
    await criarRegra.mutateAsync({
      texto_busca: textoBusca,
      operador,
      categoria_id: categoriaId,
      prioridade: Number(prioridade) || 0,
    });
    onFechar();
  }

  return (
    <Modal aberto titulo="Nova regra de categorização" onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input
          rotulo="Texto de busca"
          placeholder="Ex.: UBER, MERCADO, NETFLIX"
          value={textoBusca}
          onChange={(e) => setTextoBusca(e.target.value)}
        />
        <Select
          rotulo="Operador"
          opcoes={[
            { valor: "contem", rotulo: "Descrição contém o texto" },
            { valor: "comeca_com", rotulo: "Descrição começa com o texto" },
            { valor: "igual", rotulo: "Descrição é igual ao texto" },
          ]}
          value={operador}
          onChange={(e) => setOperador(e.target.value)}
        />
        <Select
          rotulo="Categoria"
          opcoes={[
            { valor: "", rotulo: "Selecione..." },
            ...(categorias ?? []).map((c) => {
              const pai = c.categoria_pai_id ? categorias?.find((p) => p.id === c.categoria_pai_id) : null;
              return { valor: String(c.id), rotulo: pai ? `${pai.nome} > ${c.nome}` : c.nome };
            }),
          ]}
          value={categoriaId !== null ? String(categoriaId) : ""}
          onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
        />
        <Input
          rotulo="Prioridade"
          type="number"
          dica="Regras com prioridade maior são avaliadas primeiro."
          value={prioridade}
          onChange={(e) => setPrioridade(e.target.value)}
        />
        <Button onClick={confirmar} carregando={criarRegra.isPending} disabled={!textoBusca || !categoriaId}>
          Criar regra
        </Button>
      </div>
    </Modal>
  );
}

function ModalAplicarRegra({ regra, onFechar }: { regra: Regra; onFechar: () => void }) {
  const { data: compativeis, isLoading } = usePreVisualizarRegra(regra.id);
  const aplicarRegra = useAplicarRegra();
  const [selecionados, setSelecionados] = useState<Set<number> | null>(null);
  const selecionadosAtual = selecionados ?? new Set((compativeis ?? []).map((t) => t.id));

  function alternar(id: number) {
    setSelecionados((atual) => {
      const novo = new Set(atual ?? (compativeis ?? []).map((t) => t.id));
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  async function confirmar() {
    await aplicarRegra.mutateAsync({ id: regra.id, transacaoIds: Array.from(selecionadosAtual) });
    onFechar();
  }

  return (
    <Modal aberto titulo="Revisar e aplicar regra ao histórico" onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        {!isLoading && compativeis && compativeis.length > 0 && (
          <p className="text-sm text-foreground">
            <strong>{compativeis.length}</strong> lançamento(s) histórico(s) sem categoria
            correspondem a esta regra. Todos vêm pré-selecionados — desmarque o que não deve ser
            categorizado.
          </p>
        )}
        {isLoading ? (
          <LoadingSkeleton className="h-32" />
        ) : !compativeis || compativeis.length === 0 ? (
          <EmptyState
            titulo="Nenhum lançamento compatível encontrado."
            descricao="Nenhum lançamento histórico sem categoria corresponde a esta regra agora."
          />
        ) : (
          <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
            {compativeis.map((t) => (
              <label
                key={t.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-borda px-3 py-2 text-sm"
              >
                <span className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selecionadosAtual.has(t.id)}
                    onChange={() => alternar(t.id)}
                  />
                  {t.descricao}
                  <span className="text-muted">{formatarData(t.data_transacao)}</span>
                </span>
                <Money valor={t.valor} />
              </label>
            ))}
          </div>
        )}
        <Button
          onClick={confirmar}
          carregando={aplicarRegra.isPending}
          disabled={selecionadosAtual.size === 0}
        >
          Categorizar {selecionadosAtual.size > 0 ? `(${selecionadosAtual.size})` : ""}
        </Button>
      </div>
    </Modal>
  );
}
