"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { BadgeTipo, type TipoLancamento } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DataTable, type Coluna } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterBar } from "@/components/ui/FilterBar";
import { Input } from "@/components/ui/Input";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useCartoes } from "@/features/cartoes/hooks";
import { useCategorias } from "@/features/categorias/hooks";
import { useContas } from "@/features/contas/hooks";
import {
  useAtualizarTransacao,
  useCriarParcelamento,
  useCriarTransacao,
  useExcluirTransacao,
  useTransacoes,
} from "@/features/lancamentos/hooks";
import type { Transacao } from "@/lib/api/types";
import { corFundoLancamento } from "@/lib/utils/corLancamento";
import { formatarData } from "@/lib/utils/formatadores";
import { paraDecimalApi } from "@/lib/utils/numero";

// "pagamento_fatura" não é incluído aqui de propósito: não é um tipo de
// linha em `transacoes` (fica em `pagamentos_fatura`, tabela separada —
// ver histórico de faturas em Cartões), então filtrar por ele nesta tela
// sempre devolveria erro do backend.
const OPCOES_TIPO = [
  { valor: "", rotulo: "Todos" },
  { valor: "receita", rotulo: "Receita" },
  { valor: "despesa", rotulo: "Despesa" },
  { valor: "transferencia", rotulo: "Transferência" },
];

function podeEditar(t: Transacao) {
  return t.tipo === "receita" || t.tipo === "despesa" || t.tipo === "transferencia";
}

export default function PaginaLancamentos() {
  return (
    <Suspense fallback={<LoadingSkeleton className="h-64" />}>
      <ConteudoLancamentos />
    </Suspense>
  );
}

function ConteudoLancamentos() {
  const parametros = useSearchParams();
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroContaId, setFiltroContaId] = useState("");
  const [filtroCategoriaId, setFiltroCategoriaId] = useState("");
  const [filtroTexto, setFiltroTexto] = useState("");
  const [modalAberto, setModalAberto] = useState(Boolean(parametros.get("novo")));
  const [editando, setEditando] = useState<Transacao | null>(null);
  const [excluindo, setExcluindo] = useState<Transacao | null>(null);

  const { data: contas } = useContas(false);
  const { data: cartoes } = useCartoes();
  const { data: categorias } = useCategorias();
  const { data: transacoes, isLoading } = useTransacoes({
    tipo: filtroTipo || undefined,
    conta_id: filtroContaId ? Number(filtroContaId) : undefined,
    categoria_id: filtroCategoriaId ? Number(filtroCategoriaId) : undefined,
    texto_busca: filtroTexto || undefined,
    limit: 50,
  });
  const excluirTransacao = useExcluirTransacao();

  const mapaContas = useMemo(
    () => new Map((contas ?? []).map((c) => [c.id, c.nome])),
    [contas]
  );
  const mapaCartoes = useMemo(
    () => new Map((cartoes ?? []).map((c) => [c.id, c.nome])),
    [cartoes]
  );
  const mapaCategorias = useMemo(
    () => new Map((categorias ?? []).map((c) => [c.id, c.nome])),
    [categorias]
  );

  const contagemFiltrosAtivos = [filtroTipo, filtroContaId, filtroCategoriaId, filtroTexto].filter(
    Boolean
  ).length;

  const colunas: Coluna<Transacao>[] = [
    { chave: "data", titulo: "Data", render: (t) => formatarData(t.data_transacao) },
    { chave: "tipo", titulo: "Tipo", render: (t) => <BadgeTipo tipo={t.tipo as TipoLancamento} /> },
    { chave: "descricao", titulo: "Descrição", render: (t) => t.descricao },
    {
      chave: "categoria",
      titulo: "Categoria",
      render: (t) => (t.categoria_id ? mapaCategorias.get(t.categoria_id) ?? "—" : "—"),
    },
    {
      chave: "conta",
      titulo: "Conta / cartão",
      render: (t) =>
        t.conta_id
          ? mapaContas.get(t.conta_id) ?? "—"
          : t.cartao_id
            ? (mapaCartoes.get(t.cartao_id) ?? "Cartão")
            : "—",
    },
    { chave: "valor", titulo: "Valor", render: (t) => <Money valor={t.valor} /> },
    {
      chave: "acoes",
      titulo: "",
      ocultarNoCard: false,
      render: (t) => (
        <div className="flex items-center gap-1">
          {podeEditar(t) && (
            <button
              aria-label="Editar lançamento"
              onClick={() => setEditando(t)}
              className="rounded p-1 text-muted hover:bg-borda/40"
            >
              <Pencil size={16} />
            </button>
          )}
          <button
            aria-label="Excluir lançamento"
            onClick={() => setExcluindo(t)}
            className="rounded p-1 text-despesa-texto hover:bg-despesa-fundo"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        titulo="Lançamentos"
        acoes={
          <Button onClick={() => setModalAberto(true)}>
            <Plus size={16} /> Novo lançamento
          </Button>
        }
      />

      <FilterBar contagemAtivos={contagemFiltrosAtivos}>
        <Select
          rotulo="Tipo"
          opcoes={OPCOES_TIPO}
          value={filtroTipo}
          onChange={(e) => setFiltroTipo(e.target.value)}
          className="sm:w-40"
        />
        <Select
          rotulo="Conta"
          opcoes={[{ valor: "", rotulo: "Todas" }, ...(contas ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
          value={filtroContaId}
          onChange={(e) => setFiltroContaId(e.target.value)}
          className="sm:w-44"
        />
        <Select
          rotulo="Categoria"
          opcoes={[{ valor: "", rotulo: "Todas" }, ...(categorias ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
          value={filtroCategoriaId}
          onChange={(e) => setFiltroCategoriaId(e.target.value)}
          className="sm:w-44"
        />
        <Input
          rotulo="Buscar na descrição"
          value={filtroTexto}
          onChange={(e) => setFiltroTexto(e.target.value)}
          className="sm:w-56"
        />
      </FilterBar>

      {isLoading ? (
        <LoadingSkeleton className="h-64" />
      ) : (
        <DataTable
          itens={transacoes ?? []}
          colunas={colunas}
          chaveLinha={(t) => t.id}
          corFundoLinha={(t) => corFundoLancamento(t.tipo)}
          vazio={<EmptyState titulo="Nenhum lançamento encontrado para os filtros selecionados." />}
        />
      )}

      {modalAberto && (
        <ModalLancamento tipoInicial={parametros.get("novo")} onFechar={() => setModalAberto(false)} />
      )}

      {editando && <ModalLancamento transacaoExistente={editando} onFechar={() => setEditando(null)} />}

      <ConfirmDialog
        aberto={!!excluindo}
        titulo="Excluir lançamento"
        mensagem={`Tem certeza que deseja excluir "${excluindo?.descricao}"?`}
        confirmando={excluirTransacao.isPending}
        onConfirmar={async () => {
          if (excluindo) await excluirTransacao.mutateAsync(excluindo.id);
          setExcluindo(null);
        }}
        onCancelar={() => setExcluindo(null)}
      />
    </div>
  );
}

function ModalLancamento({
  tipoInicial,
  transacaoExistente,
  onFechar,
}: {
  tipoInicial?: string | null;
  transacaoExistente?: Transacao;
  onFechar: () => void;
}) {
  const { data: contas } = useContas(false);
  const { data: cartoes } = useCartoes();
  const { data: categorias } = useCategorias();
  const criarTransacao = useCriarTransacao();
  const atualizarTransacao = useAtualizarTransacao();
  const criarParcelamento = useCriarParcelamento();
  const editando = !!transacaoExistente;
  const salvando = editando
    ? atualizarTransacao.isPending
    : criarTransacao.isPending || criarParcelamento.isPending;

  const [tipo, setTipo] = useState(transacaoExistente?.tipo ?? tipoInicial ?? "despesa");
  const [descricao, setDescricao] = useState(transacaoExistente?.descricao ?? "");
  const [valor, setValor] = useState(transacaoExistente?.valor ?? "");
  const [data, setData] = useState(
    transacaoExistente?.data_transacao ?? new Date().toISOString().slice(0, 10)
  );
  const [contaId, setContaId] = useState<number | null>(transacaoExistente?.conta_id ?? null);
  const [formaPagamento, setFormaPagamento] = useState<"conta" | "cartao">(
    transacaoExistente?.cartao_id ? "cartao" : "conta"
  );
  const [cartaoId, setCartaoId] = useState<number | null>(transacaoExistente?.cartao_id ?? null);
  const [contaDestinoId, setContaDestinoId] = useState<number | null>(
    transacaoExistente?.conta_destino_id ?? null
  );
  const [categoriaId, setCategoriaId] = useState<number | null>(
    transacaoExistente?.categoria_id ?? null
  );
  const [parcelando, setParcelando] = useState(false);
  const [totalParcelas, setTotalParcelas] = useState("2");
  const [erro, setErro] = useState<string | null>(null);

  const categoriasCompatveis = (categorias ?? []).filter(
    (c) => c.ativa && (c.tipo === "ambos" || c.tipo === tipo)
  );
  const cartoesAtivos = (cartoes ?? []).filter((c) => c.ativo);
  const usaCartao = tipo === "despesa" && formaPagamento === "cartao";
  const podeParcelar = !editando && (tipo === "despesa" || tipo === "receita");

  const valorPorParcela = (() => {
    try {
      const total = Number(paraDecimalApi(valor));
      const parcelas = Number(totalParcelas);
      if (!total || !parcelas) return null;
      return (total / parcelas).toFixed(2).replace(".", ",");
    } catch {
      return null;
    }
  })();

  async function confirmar() {
    setErro(null);
    try {
      if (transacaoExistente) {
        await atualizarTransacao.mutateAsync({
          id: transacaoExistente.id,
          dados: {
            tipo,
            descricao,
            valor: paraDecimalApi(valor),
            data_transacao: data,
            conta_id: usaCartao ? null : contaId,
            cartao_id: usaCartao ? cartaoId : null,
            conta_destino_id: tipo === "transferencia" ? contaDestinoId : null,
            categoria_id: tipo !== "transferencia" ? categoriaId : null,
          },
        });
      } else if (podeParcelar && parcelando) {
        await criarParcelamento.mutateAsync({
          tipo,
          descricao,
          valor_total: paraDecimalApi(valor),
          data_primeira_parcela: data,
          total_parcelas: Number(totalParcelas) || 2,
          conta_id: usaCartao ? null : contaId,
          cartao_id: usaCartao ? cartaoId : null,
          categoria_id: categoriaId,
        });
      } else {
        await criarTransacao.mutateAsync({
          tipo,
          descricao,
          valor: paraDecimalApi(valor),
          data_transacao: data,
          conta_id: usaCartao ? null : contaId,
          cartao_id: usaCartao ? cartaoId : null,
          conta_destino_id: tipo === "transferencia" ? contaDestinoId : null,
          categoria_id: tipo !== "transferencia" ? categoriaId : null,
        });
      }
      onFechar();
    } catch (excecao) {
      setErro(
        excecao instanceof Error
          ? excecao.message
          : `Erro ao ${editando ? "salvar" : "criar"} lançamento.`
      );
    }
  }

  return (
    <Modal aberto titulo={editando ? "Editar lançamento" : "Novo lançamento"} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Select
          rotulo="Tipo"
          opcoes={[
            { valor: "despesa", rotulo: "Despesa" },
            { valor: "receita", rotulo: "Receita" },
            { valor: "transferencia", rotulo: "Transferência" },
          ]}
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
        />
        <Input rotulo="Descrição" value={descricao} onChange={(e) => setDescricao(e.target.value)} />

        {podeParcelar && (
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={parcelando}
              onChange={(e) => setParcelando(e.target.checked)}
            />
            Dividir em parcelas
          </label>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input
            rotulo={parcelando ? "Valor total (R$)" : "Valor (R$)"}
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="Ex.: 123,45"
          />
          <Input
            rotulo={parcelando ? "Data da 1ª parcela" : "Data"}
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
          />
        </div>

        {parcelando && (
          <Input
            rotulo="Número de parcelas"
            type="number"
            min={2}
            max={60}
            value={totalParcelas}
            onChange={(e) => setTotalParcelas(e.target.value)}
            dica={valorPorParcela ? `Cada parcela: aproximadamente R$ ${valorPorParcela}` : undefined}
          />
        )}

        {tipo === "despesa" && (
          <div className="flex items-center gap-4 text-sm text-foreground">
            <span className="text-muted">Forma de pagamento</span>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="forma_pagamento"
                checked={formaPagamento === "conta"}
                onChange={() => {
                  setFormaPagamento("conta");
                  if (contaId === null && (contas ?? []).length > 0) setContaId(contas![0].id);
                }}
              />
              Conta
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="forma_pagamento"
                checked={formaPagamento === "cartao"}
                onChange={() => {
                  setFormaPagamento("cartao");
                  if (cartaoId === null && cartoesAtivos.length > 0) setCartaoId(cartoesAtivos[0].id);
                }}
              />
              Cartão de crédito
            </label>
          </div>
        )}

        {usaCartao ? (
          cartoesAtivos.length > 0 ? (
            <Select
              rotulo="Cartão"
              opcoes={cartoesAtivos.map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
              value={cartaoId !== null ? String(cartaoId) : ""}
              onChange={(e) => setCartaoId(Number(e.target.value))}
            />
          ) : (
            <p className="text-sm text-muted">
              Nenhum cartão ativo cadastrado. Cadastre um na página Cartões.
            </p>
          )
        ) : (
          <Select
            rotulo={tipo === "transferencia" ? "Conta de origem" : "Conta"}
            opcoes={(contas ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
            value={contaId !== null ? String(contaId) : ""}
            onChange={(e) => setContaId(Number(e.target.value))}
          />
        )}

        {tipo === "transferencia" ? (
          <Select
            rotulo="Conta de destino"
            opcoes={(contas ?? [])
              .filter((c) => c.id !== contaId)
              .map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
            value={contaDestinoId !== null ? String(contaDestinoId) : ""}
            onChange={(e) => setContaDestinoId(Number(e.target.value))}
          />
        ) : (
          <Select
            rotulo="Categoria"
            opcoes={[{ valor: "", rotulo: "Sem categoria" }, ...categoriasCompatveis.map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
            value={categoriaId !== null ? String(categoriaId) : ""}
            onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
          />
        )}

        {erro && (
          <p role="alert" className="text-sm text-despesa-texto">
            {erro}
          </p>
        )}

        <Button onClick={confirmar} carregando={salvando}>
          {editando
            ? "Salvar alterações"
            : podeParcelar && parcelando
              ? `Criar ${totalParcelas || "2"} parcelas`
              : "Criar lançamento"}
        </Button>
      </div>
    </Modal>
  );
}
