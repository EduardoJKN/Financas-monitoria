"use client";

import { useState } from "react";
import { History, Pencil, Plus } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { LoadingCards, LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useContas } from "@/features/contas/hooks";
import {
  useAtualizarCartao,
  useCartoes,
  useCriarCartao,
  useFaturas,
  usePagarFatura,
} from "@/features/cartoes/hooks";
import type { Cartao } from "@/lib/api/types";
import { formatarData } from "@/lib/utils/formatadores";
import { paraDecimalApi } from "@/lib/utils/numero";

export default function PaginaCartoes() {
  const { data: cartoes, isLoading } = useCartoes();
  const [modalNovoCartao, setModalNovoCartao] = useState(false);
  const [cartaoPagando, setCartaoPagando] = useState<Cartao | null>(null);
  const [cartaoEditando, setCartaoEditando] = useState<Cartao | null>(null);
  const [cartaoHistorico, setCartaoHistorico] = useState<Cartao | null>(null);

  return (
    <div>
      <PageHeader
        titulo="Cartões"
        acoes={
          <Button onClick={() => setModalNovoCartao(true)}>
            <Plus size={16} /> Novo cartão
          </Button>
        }
      />

      {isLoading ? (
        <LoadingCards quantidade={2} />
      ) : !cartoes || cartoes.length === 0 ? (
        <EmptyState titulo="Nenhum cartão cadastrado ainda." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {cartoes.map((cartao) => {
            const limite = Number(cartao.limite);
            const utilizado = Number(cartao.limite_utilizado ?? 0);
            const percentualUso = limite > 0 ? Math.min((utilizado / limite) * 100, 100) : 0;
            const corBarra =
              percentualUso >= 90
                ? "bg-despesa-texto"
                : percentualUso >= 70
                  ? "bg-fatura-texto"
                  : "bg-receita-texto";

            return (
              <Card key={cartao.id} className={`flex flex-col gap-3 ${!cartao.ativo ? "opacity-60" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-foreground">{cartao.nome}</p>
                    <p className="text-sm text-muted">{cartao.instituicao || "Sem instituição"}</p>
                  </div>
                  {!cartao.ativo && <Badge>Inativo</Badge>}
                </div>

                <div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-borda">
                    <div
                      className={`h-full rounded-full ${corBarra}`}
                      style={{ width: `${percentualUso}%` }}
                    />
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-muted">
                    <span>
                      Usado: <Money valor={cartao.limite_utilizado} /> ({percentualUso.toFixed(0)}%)
                    </span>
                    <span>
                      Disponível: <Money valor={cartao.limite_disponivel} />
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted">
                    Limite total: <Money valor={cartao.limite} />
                  </p>
                </div>

                <p className="text-xs text-muted">
                  Fecha dia {cartao.dia_fechamento} · Vence dia {cartao.dia_vencimento}
                </p>

                {cartao.fatura_atual && (
                  <div className="rounded-lg border border-borda p-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-muted">
                        Fatura atual — vence {formatarData(cartao.fatura_atual.data_vencimento)}
                      </p>
                      <Badge>{cartao.fatura_atual.status_exibicao}</Badge>
                    </div>
                    <p className="font-medium text-foreground">
                      <Money valor={cartao.fatura_atual.saldo_devedor} />
                    </p>
                    {Number(cartao.fatura_atual.saldo_devedor) > 0 && (
                      <Button
                        variante="secundaria"
                        className="mt-2"
                        onClick={() => setCartaoPagando(cartao)}
                      >
                        Pagar fatura
                      </Button>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button variante="fantasma" onClick={() => setCartaoEditando(cartao)}>
                    <Pencil size={14} /> Editar
                  </Button>
                  <Button variante="fantasma" onClick={() => setCartaoHistorico(cartao)}>
                    <History size={14} /> Faturas anteriores
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {modalNovoCartao && <ModalNovoCartao onFechar={() => setModalNovoCartao(false)} />}
      {cartaoPagando && (
        <ModalPagarFatura cartao={cartaoPagando} onFechar={() => setCartaoPagando(null)} />
      )}
      {cartaoEditando && (
        <ModalEditarCartao cartao={cartaoEditando} onFechar={() => setCartaoEditando(null)} />
      )}
      {cartaoHistorico && (
        <ModalHistoricoFaturas cartao={cartaoHistorico} onFechar={() => setCartaoHistorico(null)} />
      )}
    </div>
  );
}

function ModalNovoCartao({ onFechar }: { onFechar: () => void }) {
  const criarCartao = useCriarCartao();
  const [nome, setNome] = useState("");
  const [instituicao, setInstituicao] = useState("");
  const [limite, setLimite] = useState("0");
  const [diaFechamento, setDiaFechamento] = useState("1");
  const [diaVencimento, setDiaVencimento] = useState("10");

  async function confirmar() {
    await criarCartao.mutateAsync({
      nome,
      instituicao: instituicao || null,
      limite: paraDecimalApi(limite),
      dia_fechamento: Number(diaFechamento),
      dia_vencimento: Number(diaVencimento),
    });
    onFechar();
  }

  return (
    <Modal aberto titulo="Novo cartão" onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
        <Input
          rotulo="Instituição (opcional)"
          value={instituicao}
          onChange={(e) => setInstituicao(e.target.value)}
        />
        <Input rotulo="Limite (R$)" value={limite} onChange={(e) => setLimite(e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <Input
            rotulo="Dia de fechamento"
            type="number"
            min={1}
            max={31}
            value={diaFechamento}
            onChange={(e) => setDiaFechamento(e.target.value)}
          />
          <Input
            rotulo="Dia de vencimento"
            type="number"
            min={1}
            max={31}
            value={diaVencimento}
            onChange={(e) => setDiaVencimento(e.target.value)}
          />
        </div>
        <Button onClick={confirmar} carregando={criarCartao.isPending} disabled={!nome}>
          Criar cartão
        </Button>
      </div>
    </Modal>
  );
}

function ModalEditarCartao({ cartao, onFechar }: { cartao: Cartao; onFechar: () => void }) {
  const atualizarCartao = useAtualizarCartao();
  const [nome, setNome] = useState(cartao.nome);
  const [instituicao, setInstituicao] = useState(cartao.instituicao ?? "");
  const [limite, setLimite] = useState(cartao.limite);
  const [diaFechamento, setDiaFechamento] = useState(String(cartao.dia_fechamento));
  const [diaVencimento, setDiaVencimento] = useState(String(cartao.dia_vencimento));

  async function confirmar() {
    await atualizarCartao.mutateAsync({
      id: cartao.id,
      dados: {
        nome,
        instituicao: instituicao || null,
        limite: paraDecimalApi(limite),
        dia_fechamento: Number(diaFechamento),
        dia_vencimento: Number(diaVencimento),
      },
    });
    onFechar();
  }

  return (
    <Modal aberto titulo={`Editar ${cartao.nome}`} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
        <Input
          rotulo="Instituição (opcional)"
          value={instituicao}
          onChange={(e) => setInstituicao(e.target.value)}
        />
        <Input rotulo="Limite (R$)" value={limite} onChange={(e) => setLimite(e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <Input
            rotulo="Dia de fechamento"
            type="number"
            min={1}
            max={31}
            value={diaFechamento}
            onChange={(e) => setDiaFechamento(e.target.value)}
          />
          <Input
            rotulo="Dia de vencimento"
            type="number"
            min={1}
            max={31}
            value={diaVencimento}
            onChange={(e) => setDiaVencimento(e.target.value)}
          />
        </div>
        <Button onClick={confirmar} carregando={atualizarCartao.isPending} disabled={!nome}>
          Salvar alterações
        </Button>
        <Button
          variante="fantasma"
          onClick={() => atualizarCartao.mutate({ id: cartao.id, dados: { ativo: !cartao.ativo } })}
        >
          {cartao.ativo ? "Desativar cartão" : "Ativar cartão"}
        </Button>
      </div>
    </Modal>
  );
}

function ModalPagarFatura({ cartao, onFechar }: { cartao: Cartao; onFechar: () => void }) {
  const { data: contas } = useContas(false);
  const pagarFatura = usePagarFatura();
  const [contaId, setContaId] = useState<number | null>(contas?.[0]?.id ?? null);
  const [valor, setValor] = useState(cartao.fatura_atual?.saldo_devedor ?? "0");
  const [dataPagamento, setDataPagamento] = useState(new Date().toISOString().slice(0, 10));

  async function confirmar() {
    if (!cartao.fatura_atual || !contaId) return;
    await pagarFatura.mutateAsync({
      faturaId: cartao.fatura_atual.id,
      dados: { conta_id: contaId, valor: paraDecimalApi(valor), data_pagamento: dataPagamento },
    });
    onFechar();
  }

  return (
    <Modal aberto titulo={`Pagar fatura — ${cartao.nome}`} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Select
          rotulo="Pagar com a conta"
          opcoes={(contas ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))}
          value={contaId !== null ? String(contaId) : ""}
          onChange={(e) => setContaId(Number(e.target.value))}
        />
        <Input rotulo="Valor (R$)" value={valor} onChange={(e) => setValor(e.target.value)} />
        <Input
          rotulo="Data do pagamento"
          type="date"
          value={dataPagamento}
          onChange={(e) => setDataPagamento(e.target.value)}
        />
        <Button onClick={confirmar} carregando={pagarFatura.isPending}>
          Confirmar pagamento
        </Button>
      </div>
    </Modal>
  );
}

function ModalHistoricoFaturas({ cartao, onFechar }: { cartao: Cartao; onFechar: () => void }) {
  const { data: faturas, isLoading } = useFaturas(cartao.id);
  const ordenadas = [...(faturas ?? [])].sort((a, b) =>
    b.mes_referencia.localeCompare(a.mes_referencia)
  );

  return (
    <Modal aberto titulo={`Faturas anteriores — ${cartao.nome}`} onFechar={onFechar}>
      {isLoading ? (
        <LoadingSkeleton className="h-32" />
      ) : ordenadas.length === 0 ? (
        <EmptyState titulo="Nenhuma fatura encontrada para este cartão ainda." />
      ) : (
        <div className="flex flex-col gap-2">
          {ordenadas.map((fatura) => (
            <div
              key={fatura.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-borda px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-foreground">{fatura.mes_referencia}</p>
                <p className="text-xs text-muted">Vence {formatarData(fatura.data_vencimento)}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge>{fatura.status_exibicao}</Badge>
                <Money valor={fatura.total} className="font-medium text-foreground" />
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
