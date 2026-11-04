"use client";

import { useState } from "react";
import { CheckCircle2, AlertTriangle, Pencil, Plus } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { LoadingCards } from "@/components/ui/LoadingSkeleton";
import { Modal } from "@/components/ui/Modal";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import {
  useAtualizarConta,
  useConciliarConta,
  useContas,
  useCriarConta,
} from "@/features/contas/hooks";
import type { Conta } from "@/lib/api/types";
import { formatarData } from "@/lib/utils/formatadores";
import { paraDecimalApi } from "@/lib/utils/numero";

const TIPOS_CONTA = [
  { valor: "conta_corrente", rotulo: "Conta corrente" },
  { valor: "conta_digital", rotulo: "Conta digital" },
  { valor: "poupanca", rotulo: "Poupança" },
  { valor: "dinheiro", rotulo: "Dinheiro" },
  { valor: "investimento", rotulo: "Investimento" },
  { valor: "outro", rotulo: "Outro" },
];

export default function PaginaContas() {
  const { data: contas, isLoading } = useContas();
  const criarConta = useCriarConta();
  const atualizarConta = useAtualizarConta();
  const [modalNovaConta, setModalNovaConta] = useState(false);
  const [contaConciliando, setContaConciliando] = useState<Conta | null>(null);
  const [contaEditando, setContaEditando] = useState<Conta | null>(null);

  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("conta_corrente");
  const [saldoInicial, setSaldoInicial] = useState("0");

  async function aoCriarConta() {
    await criarConta.mutateAsync({ nome, tipo, saldo_inicial: paraDecimalApi(saldoInicial) });
    setModalNovaConta(false);
    setNome("");
    setSaldoInicial("0");
  }

  return (
    <div>
      <PageHeader
        titulo="Contas"
        acoes={
          <Button onClick={() => setModalNovaConta(true)}>
            <Plus size={16} /> Nova conta
          </Button>
        }
      />

      {isLoading ? (
        <LoadingCards quantidade={3} />
      ) : !contas || contas.length === 0 ? (
        <EmptyState titulo="Nenhuma conta cadastrada ainda." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {contas.map((conta) => (
            <Card
              key={conta.id}
              className={`flex flex-col gap-3 ${!conta.ativa ? "opacity-60" : ""}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-foreground">{conta.nome}</p>
                  <p className="text-sm text-muted">{conta.instituicao || "Sem instituição"}</p>
                </div>
                {!conta.ativa && <Badge>Inativa</Badge>}
              </div>

              <Money valor={conta.saldo_inicial} className="text-2xl font-semibold text-foreground" />

              {conta.data_saldo_inicial ? (
                <div className="flex items-center gap-1.5 rounded-lg bg-receita-fundo px-2.5 py-1.5 text-xs text-receita-texto">
                  <CheckCircle2 size={14} />
                  <span>Saldo conciliado em {formatarData(conta.data_saldo_inicial)}</span>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-despesa-fundo px-2.5 py-1.5 text-xs text-despesa-texto">
                  <span className="flex items-center gap-1.5">
                    <AlertTriangle size={14} />
                    Saldo precisa de conciliação
                  </span>
                  <button
                    onClick={() => setContaConciliando(conta)}
                    className="font-medium underline underline-offset-2"
                  >
                    Conciliar agora
                  </button>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <Button variante="secundaria" onClick={() => setContaConciliando(conta)}>
                  Conciliar
                </Button>
                <Button variante="fantasma" onClick={() => setContaEditando(conta)}>
                  <Pencil size={14} /> Editar
                </Button>
                <Button
                  variante="fantasma"
                  onClick={() => atualizarConta.mutate({ id: conta.id, dados: { ativa: !conta.ativa } })}
                >
                  {conta.ativa ? "Desativar" : "Ativar"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal aberto={modalNovaConta} titulo="Nova conta" onFechar={() => setModalNovaConta(false)}>
        <div className="flex flex-col gap-4">
          <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
          <Select rotulo="Tipo" opcoes={TIPOS_CONTA} value={tipo} onChange={(e) => setTipo(e.target.value)} />
          <Input
            rotulo="Saldo inicial (R$)"
            value={saldoInicial}
            onChange={(e) => setSaldoInicial(e.target.value)}
          />
          <Button onClick={aoCriarConta} carregando={criarConta.isPending}>
            Criar conta
          </Button>
        </div>
      </Modal>

      {contaConciliando && (
        <ModalConciliacao
          conta={contaConciliando}
          onFechar={() => setContaConciliando(null)}
        />
      )}

      {contaEditando && (
        <ModalEditarConta conta={contaEditando} onFechar={() => setContaEditando(null)} />
      )}
    </div>
  );
}

function ModalEditarConta({ conta, onFechar }: { conta: Conta; onFechar: () => void }) {
  const atualizarConta = useAtualizarConta();
  const [nome, setNome] = useState(conta.nome);
  const [tipo, setTipo] = useState(conta.tipo);
  const [instituicao, setInstituicao] = useState(conta.instituicao ?? "");

  async function confirmar() {
    await atualizarConta.mutateAsync({
      id: conta.id,
      dados: { nome, tipo, instituicao: instituicao || null },
    });
    onFechar();
  }

  return (
    <Modal aberto titulo={`Editar ${conta.nome}`} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
        <Select rotulo="Tipo" opcoes={TIPOS_CONTA} value={tipo} onChange={(e) => setTipo(e.target.value)} />
        <Input
          rotulo="Instituição (opcional)"
          value={instituicao}
          onChange={(e) => setInstituicao(e.target.value)}
        />
        <Button onClick={confirmar} carregando={atualizarConta.isPending} disabled={!nome}>
          Salvar alterações
        </Button>
      </div>
    </Modal>
  );
}

function ModalConciliacao({ conta, onFechar }: { conta: Conta; onFechar: () => void }) {
  const conciliar = useConciliarConta();
  const [dataReferencia, setDataReferencia] = useState(new Date().toISOString().slice(0, 10));
  const [saldoInformado, setSaldoInformado] = useState("");

  async function confirmar() {
    await conciliar.mutateAsync({
      id: conta.id,
      data_referencia: dataReferencia,
      saldo_informado: paraDecimalApi(saldoInformado),
    });
    onFechar();
  }

  return (
    <Modal aberto titulo={`Conciliar ${conta.nome}`} onFechar={onFechar}>
      <div className="flex flex-col gap-4">
        <Input
          rotulo="Data de referência"
          type="date"
          value={dataReferencia}
          onChange={(e) => setDataReferencia(e.target.value)}
        />
        <Input
          rotulo="Saldo informado pelo banco (R$)"
          value={saldoInformado}
          onChange={(e) => setSaldoInformado(e.target.value)}
          placeholder="Ex.: 1234,56"
        />
        <p className="text-xs text-muted">
          Lançamentos até essa data não serão somados de novo no cálculo do saldo atual.
        </p>
        <Button onClick={confirmar} carregando={conciliar.isPending}>
          Confirmar conciliação
        </Button>
      </div>
    </Modal>
  );
}
