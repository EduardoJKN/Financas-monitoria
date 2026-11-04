"use client";

import { useMemo, useState } from "react";
import { CornerDownRight, Pencil, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import {
  useAtualizarCategoria,
  useCategorias,
  useCriarCategoria,
  useExcluirCategoria,
} from "@/features/categorias/hooks";
import type { Categoria } from "@/lib/api/types";

const ROTULO_TIPO: Record<string, string> = { receita: "Receita", despesa: "Despesa", ambos: "Ambos" };

function LinhaCategoria({
  categoria,
  subcategoria,
  onNovaSubcategoria,
  onEditar,
  onExcluir,
  atualizarCategoria,
}: {
  categoria: Categoria;
  subcategoria: boolean;
  onNovaSubcategoria?: () => void;
  onEditar: () => void;
  onExcluir: () => void;
  atualizarCategoria: ReturnType<typeof useAtualizarCategoria>;
}) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border border-borda px-3 py-2 ${
        subcategoria ? "ml-6 border-dashed bg-superficie/50" : ""
      }`}
    >
      <div className="flex items-center gap-2">
        {subcategoria && <CornerDownRight size={14} className="text-muted" />}
        <span className="text-sm text-foreground">{categoria.nome}</span>
        <Badge>{ROTULO_TIPO[categoria.tipo]}</Badge>
        {!categoria.ativa && <Badge>Inativa</Badge>}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {onNovaSubcategoria && (
          <Button variante="fantasma" onClick={onNovaSubcategoria}>
            <Plus size={14} /> Subcategoria
          </Button>
        )}
        <Button
          variante="fantasma"
          onClick={() => atualizarCategoria.mutate({ id: categoria.id, dados: { ativa: !categoria.ativa } })}
        >
          {categoria.ativa ? "Desativar" : "Ativar"}
        </Button>
        <button
          aria-label="Editar categoria"
          onClick={onEditar}
          className="rounded p-1 text-muted hover:bg-borda/40"
        >
          <Pencil size={16} />
        </button>
        <button
          aria-label="Excluir categoria"
          onClick={onExcluir}
          className="rounded p-1 text-despesa-texto hover:bg-despesa-fundo"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}

export default function PaginaCategorias() {
  const { data: categorias, isLoading } = useCategorias();
  const excluirCategoria = useExcluirCategoria();
  const atualizarCategoria = useAtualizarCategoria();
  const [modalAberto, setModalAberto] = useState(false);
  const [categoriaPaiNova, setCategoriaPaiNova] = useState<Categoria | null>(null);
  const [editando, setEditando] = useState<Categoria | null>(null);
  const [excluindo, setExcluindo] = useState<Categoria | null>(null);

  const arvore = useMemo(() => {
    const raizes = (categorias ?? []).filter((c) => c.categoria_pai_id === null);
    const filhosPorPai = new Map<number, Categoria[]>();
    for (const c of categorias ?? []) {
      if (c.categoria_pai_id === null) continue;
      const lista = filhosPorPai.get(c.categoria_pai_id) ?? [];
      lista.push(c);
      filhosPorPai.set(c.categoria_pai_id, lista);
    }
    return raizes.map((raiz) => ({ raiz, filhos: filhosPorPai.get(raiz.id) ?? [] }));
  }, [categorias]);

  function abrirNovaSubcategoria(pai: Categoria) {
    setCategoriaPaiNova(pai);
    setModalAberto(true);
  }

  function fecharModal() {
    setModalAberto(false);
    setCategoriaPaiNova(null);
  }

  return (
    <div>
      <PageHeader
        titulo="Categorias"
        descricao="Organize em categorias e subcategorias para enxergar melhor para onde o dinheiro vai."
        acoes={
          <Button onClick={() => setModalAberto(true)}>
            <Plus size={16} /> Nova categoria
          </Button>
        }
      />

      {isLoading ? (
        <LoadingSkeleton className="h-48" />
      ) : !categorias || categorias.length === 0 ? (
        <EmptyState titulo="Nenhuma categoria cadastrada ainda." />
      ) : (
        <div className="flex flex-col gap-2">
          {arvore.map(({ raiz, filhos }) => (
            <div key={raiz.id} className="flex flex-col gap-2">
              <LinhaCategoria
                categoria={raiz}
                subcategoria={false}
                onNovaSubcategoria={() => abrirNovaSubcategoria(raiz)}
                onEditar={() => setEditando(raiz)}
                onExcluir={() => setExcluindo(raiz)}
                atualizarCategoria={atualizarCategoria}
              />
              {filhos.map((filho) => (
                <LinhaCategoria
                  key={filho.id}
                  categoria={filho}
                  subcategoria
                  onEditar={() => setEditando(filho)}
                  onExcluir={() => setExcluindo(filho)}
                  atualizarCategoria={atualizarCategoria}
                />
              ))}
            </div>
          ))}
        </div>
      )}

      {modalAberto && (
        <ModalCategoria categoriaPaiInicial={categoriaPaiNova} onFechar={fecharModal} />
      )}

      {editando && <ModalCategoria categoriaExistente={editando} onFechar={() => setEditando(null)} />}

      <ConfirmDialog
        aberto={!!excluindo}
        titulo="Excluir categoria"
        mensagem={`Tem certeza que deseja excluir "${excluindo?.nome}"?`}
        confirmando={excluirCategoria.isPending}
        onConfirmar={async () => {
          if (excluindo) await excluirCategoria.mutateAsync(excluindo.id);
          setExcluindo(null);
        }}
        onCancelar={() => setExcluindo(null)}
      />
    </div>
  );
}

function ModalCategoria({
  categoriaExistente,
  categoriaPaiInicial,
  onFechar,
}: {
  categoriaExistente?: Categoria;
  categoriaPaiInicial?: Categoria | null;
  onFechar: () => void;
}) {
  const { data: categorias } = useCategorias();
  const criarCategoria = useCriarCategoria();
  const atualizarCategoria = useAtualizarCategoria();
  const editando = !!categoriaExistente;
  const salvando = editando ? atualizarCategoria.isPending : criarCategoria.isPending;

  const [nome, setNome] = useState(categoriaExistente?.nome ?? "");
  const [tipo, setTipo] = useState<string>(
    categoriaExistente?.tipo ?? categoriaPaiInicial?.tipo ?? "despesa"
  );
  const [categoriaPaiId, setCategoriaPaiId] = useState<number | null>(
    categoriaExistente?.categoria_pai_id ?? categoriaPaiInicial?.id ?? null
  );

  const opcoesCategoriaPai = (categorias ?? []).filter(
    (c) => c.categoria_pai_id === null && c.id !== categoriaExistente?.id && (c.tipo === "ambos" || c.tipo === tipo)
  );

  async function confirmar() {
    if (categoriaExistente) {
      await atualizarCategoria.mutateAsync({
        id: categoriaExistente.id,
        dados: { nome, tipo, categoria_pai_id: categoriaPaiId },
      });
    } else {
      await criarCategoria.mutateAsync({ nome, tipo, categoria_pai_id: categoriaPaiId });
    }
    onFechar();
  }

  const titulo = editando
    ? "Editar categoria"
    : categoriaPaiInicial
      ? `Nova subcategoria de ${categoriaPaiInicial.nome}`
      : "Nova categoria";

  return (
    <Modal aberto titulo={titulo} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
        <Select
          rotulo="Tipo"
          opcoes={[
            { valor: "despesa", rotulo: "Despesa" },
            { valor: "receita", rotulo: "Receita" },
            { valor: "ambos", rotulo: "Ambos" },
          ]}
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
        />
        <div>
          <Select
            rotulo="Categoria pai (opcional)"
            opcoes={[
              { valor: "", rotulo: "Nenhuma — é uma categoria principal" },
              ...opcoesCategoriaPai.map((c) => ({ valor: String(c.id), rotulo: c.nome })),
            ]}
            value={categoriaPaiId !== null ? String(categoriaPaiId) : ""}
            onChange={(e) => setCategoriaPaiId(e.target.value ? Number(e.target.value) : null)}
          />
          <p className="mt-1 text-xs text-muted">Deixe em branco para criar uma categoria principal.</p>
        </div>
        <Button onClick={confirmar} carregando={salvando} disabled={!nome}>
          {editando ? "Salvar alterações" : "Criar categoria"}
        </Button>
      </div>
    </Modal>
  );
}
