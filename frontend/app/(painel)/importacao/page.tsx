"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Upload } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Money } from "@/components/ui/Money";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useCartoes } from "@/features/cartoes/hooks";
import { useCategorias } from "@/features/categorias/hooks";
import { useContas } from "@/features/contas/hooks";
import { apiFetch, apiUpload } from "@/lib/api/client";
import { formatarData } from "@/lib/utils/formatadores";

type LinhaPrevia = {
  indice: number;
  data: string | null;
  descricao: string;
  valor: string | null;
  tipo: "receita" | "despesa" | null;
  status: "ok" | "duplicada" | "revisar" | "erro";
  mensagem: string;
  possivel_transferencia: boolean;
  possivel_pagamento_fatura: boolean;
  categoria_sugerida_id: number | null;
};

type RespostaMapeamento = {
  fase: "mapeamento_necessario";
  colunas_disponiveis: string[];
  delimitador_detectado: string;
  encoding_detectado: string;
  cabecalho_detectado: boolean;
  total_linhas: number;
  amostra: Record<string, string>[];
};

type RespostaPrevia = {
  fase: "pre_visualizacao";
  linhas: LinhaPrevia[];
  total_lidas: number;
  saldo?: {
    saldo_banco: string;
    data_saldo: string;
    saldo_aplicativo: string;
    diferenca: string;
  } | null;
};

type LinhaRevisao = {
  incluida: boolean;
  classificacao: "normal" | "transferencia" | "pagamento_fatura";
  tipo: "receita" | "despesa";
  categoriaId: number | null;
  outraContaId: number | null;
  cartaoId: number | null;
};

const ETAPAS = ["Arquivo", "Configuração", "Pré-visualização", "Revisão", "Confirmar"] as const;

export default function PaginaImportacao() {
  const { data: contas } = useContas(false);
  const { data: cartoes } = useCartoes();
  const { data: categorias } = useCategorias();

  const [etapa, setEtapa] = useState<number>(0);
  const [contaId, setContaId] = useState<number | null>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const [mapeamento, setMapeamento] = useState<RespostaMapeamento | null>(null);
  const [colData, setColData] = useState("");
  const [colValor, setColValor] = useState("");
  const [colDescricao, setColDescricao] = useState("");
  const [colTipo, setColTipo] = useState("");
  const [mapeamentoTipo, setMapeamentoTipo] = useState<Record<string, "receita" | "despesa" | "">>({});
  const [delimitador, setDelimitador] = useState("");
  const [encoding, setEncoding] = useState("");

  const [previa, setPrevia] = useState<RespostaPrevia | null>(null);
  const [revisao, setRevisao] = useState<Map<number, LinhaRevisao>>(new Map());
  const [resultado, setResultado] = useState<{ importadas: number; total: number; com_erro: Array<{ indice: number; descricao: string; motivo: string }> } | null>(null);

  const ehOfx = arquivo?.name.toLowerCase().endsWith(".ofx") ?? false;

  function normalizarTexto(texto: string) {
    return texto
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  function inferirMapeamentoPadrao(valorBruto: string): "receita" | "despesa" | "" {
    const normalizado = normalizarTexto(valorBruto);
    if (["receit", "credit", "entrada"].some((p) => normalizado.includes(p))) return "receita";
    if (["despes", "debit", "saida"].some((p) => normalizado.includes(p))) return "despesa";
    return "";
  }

  const valoresDistintosTipo = useMemo(() => {
    if (!colTipo || !mapeamento) return [];
    const vistos = new Set<string>();
    for (const linha of mapeamento.amostra) {
      const valor = String(linha[colTipo] ?? "").trim();
      if (valor) vistos.add(valor);
    }
    return Array.from(vistos);
  }, [colTipo, mapeamento]);

  function selecionarColunaTipo(coluna: string) {
    setColTipo(coluna);
    if (!coluna) {
      setMapeamentoTipo({});
      return;
    }
    const vistos = new Set<string>();
    for (const linha of mapeamento?.amostra ?? []) {
      const valor = String(linha[coluna] ?? "").trim();
      if (valor) vistos.add(valor);
    }
    const padrao: Record<string, "receita" | "despesa" | ""> = {};
    for (const valor of vistos) padrao[valor] = inferirMapeamentoPadrao(valor);
    setMapeamentoTipo(padrao);
  }

  function construirFormData(extra?: Record<string, string>) {
    const formData = new FormData();
    if (arquivo) formData.append("arquivo", arquivo);
    formData.append("conta_id_importacao", String(contaId));
    if (extra) {
      for (const [chave, valor] of Object.entries(extra)) formData.append(chave, valor);
    }
    return formData;
  }

  function inicializarRevisao(linhas: LinhaPrevia[]) {
    const mapa = new Map<number, LinhaRevisao>();
    for (const linha of linhas) {
      mapa.set(linha.indice, {
        incluida: linha.status === "ok" || linha.status === "duplicada",
        classificacao: "normal",
        tipo: linha.tipo ?? "despesa",
        categoriaId: linha.categoria_sugerida_id,
        outraContaId: null,
        cartaoId: null,
      });
    }
    setRevisao(mapa);
  }

  async function enviarArquivo() {
    if (!arquivo || !contaId) return;
    setCarregando(true);
    setErro(null);
    try {
      if (ehOfx) {
        const resposta = await apiUpload<RespostaPrevia>(
          "/api/v1/importacoes/ofx/previsualizar",
          construirFormData()
        );
        setPrevia(resposta);
        inicializarRevisao(resposta.linhas);
        setEtapa(2);
      } else {
        const resposta = await apiUpload<RespostaMapeamento | RespostaPrevia>(
          "/api/v1/importacoes/csv/previsualizar",
          construirFormData()
        );
        if (resposta.fase === "mapeamento_necessario") {
          setMapeamento(resposta);
          setDelimitador(resposta.delimitador_detectado);
          setEncoding(resposta.encoding_detectado);
          setEtapa(1);
        } else {
          setPrevia(resposta);
          inicializarRevisao(resposta.linhas);
          setEtapa(2);
        }
      }
    } catch (excecao) {
      setErro(excecao instanceof Error ? excecao.message : "Erro ao processar o arquivo.");
    } finally {
      setCarregando(false);
    }
  }

  async function confirmarMapeamento() {
    if (!colData || !colValor || !colDescricao) return;
    setCarregando(true);
    setErro(null);
    try {
      const extra: Record<string, string> = {
        col_data: colData,
        col_valor: colValor,
        col_descricao: colDescricao,
        delimitador,
        encoding,
      };
      if (colTipo) {
        extra.col_tipo = colTipo;
        extra.mapeamento_tipo = JSON.stringify(
          Object.fromEntries(valoresDistintosTipo.map((v) => [v, mapeamentoTipo[v] || null]))
        );
      }
      const resposta = await apiUpload<RespostaPrevia>(
        "/api/v1/importacoes/csv/previsualizar",
        construirFormData(extra)
      );
      setPrevia(resposta);
      inicializarRevisao(resposta.linhas);
      setEtapa(2);
    } catch (excecao) {
      setErro(excecao instanceof Error ? excecao.message : "Erro ao interpretar o arquivo.");
    } finally {
      setCarregando(false);
    }
  }

  function atualizarLinha(indice: number, campos: Partial<LinhaRevisao>) {
    setRevisao((atual) => {
      const novo = new Map(atual);
      const existente = novo.get(indice);
      if (existente) novo.set(indice, { ...existente, ...campos });
      return novo;
    });
  }

  async function confirmarImportacao() {
    if (!previa || !contaId) return;
    setCarregando(true);
    setErro(null);
    try {
      const linhasParaEnviar = previa.linhas
        .filter((l) => l.status !== "erro" && revisao.get(l.indice)?.incluida)
        .map((l) => {
          const r = revisao.get(l.indice)!;
          return {
            indice: l.indice,
            classificacao: r.classificacao,
            tipo: r.tipo,
            descricao: l.descricao,
            valor: l.valor,
            data_transacao: l.data,
            categoria_id: r.classificacao === "normal" ? r.categoriaId : null,
            outra_conta_id: r.classificacao === "transferencia" ? r.outraContaId : null,
            cartao_vinculado_id: r.classificacao === "pagamento_fatura" ? r.cartaoId : null,
          };
        });

      const resultadoFinal = await apiFetch<{
        importadas: number;
        total: number;
        com_erro: Array<{ indice: number; descricao: string; motivo: string }>;
      }>("/api/v1/importacoes/confirmar", {
        method: "POST",
        body: { conta_id_importacao: contaId, linhas: linhasParaEnviar },
      });
      setResultado(resultadoFinal);
      setEtapa(4);
    } catch (excecao) {
      setErro(excecao instanceof Error ? excecao.message : "Erro ao confirmar a importação.");
    } finally {
      setCarregando(false);
    }
  }

  function reiniciar() {
    setEtapa(0);
    setArquivo(null);
    setMapeamento(null);
    setColTipo("");
    setMapeamentoTipo({});
    setPrevia(null);
    setRevisao(new Map());
    setResultado(null);
    setErro(null);
  }

  const quantidadeIncluida = useMemo(
    () => Array.from(revisao.values()).filter((r) => r.incluida).length,
    [revisao]
  );

  const contagemPorStatus = useMemo(() => {
    const linhas = previa?.linhas ?? [];
    return {
      ok: linhas.filter((l) => l.status === "ok").length,
      duplicada: linhas.filter((l) => l.status === "duplicada").length,
      revisar: linhas.filter((l) => l.status === "revisar").length,
      erro: linhas.filter((l) => l.status === "erro").length,
    };
  }, [previa]);

  const quantidadeIgnorada = useMemo(
    () =>
      (previa?.linhas ?? []).filter(
        (l) => l.status !== "erro" && !revisao.get(l.indice)?.incluida
      ).length,
    [previa, revisao]
  );

  return (
    <div>
      <PageHeader titulo="Importação" descricao="Importe extratos em CSV ou OFX." />

      <ol className="mb-6 flex flex-wrap gap-2 text-xs font-medium text-muted">
        {ETAPAS.map((nome, indice) => (
          <li
            key={nome}
            className={`rounded-full px-3 py-1 ${
              indice === etapa ? "bg-primaria text-primaria-foreground" : "border border-borda"
            }`}
          >
            {indice + 1}. {nome}
          </li>
        ))}
      </ol>

      {erro && (
        <p role="alert" className="mb-4 rounded-lg border border-despesa-texto/30 bg-despesa-fundo p-3 text-sm text-despesa-texto">
          {erro}
        </p>
      )}

      {etapa === 0 && (
        <Card className="flex flex-col gap-4">
          <Select
            rotulo="Conta de destino"
            opcoes={[{ valor: "", rotulo: "Selecione..." }, ...(contas ?? []).map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
            value={contaId !== null ? String(contaId) : ""}
            onChange={(e) => setContaId(e.target.value ? Number(e.target.value) : null)}
          />
          <div>
            <label htmlFor="arquivo-importacao" className="mb-1 block text-sm font-medium text-foreground">
              Arquivo (CSV ou OFX, até 10 MB)
            </label>
            <input
              id="arquivo-importacao"
              type="file"
              accept=".csv,.ofx"
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
              className="text-sm text-foreground"
            />
          </div>
          <Button onClick={enviarArquivo} carregando={carregando} disabled={!arquivo || !contaId}>
            <Upload size={16} /> Continuar
          </Button>
        </Card>
      )}

      {etapa === 1 && mapeamento && (
        <Card className="flex flex-col gap-4">
          <p className="text-sm text-muted">
            Não foi possível reconhecer automaticamente as colunas. Selecione qual coluna do
            arquivo corresponde a cada campo.
          </p>

          <div className="overflow-x-auto rounded-lg border border-borda">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-borda text-left text-muted">
                  {mapeamento.colunas_disponiveis.map((c) => (
                    <th key={c} className="px-2 py-1 font-medium">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mapeamento.amostra.slice(0, 5).map((linha, i) => (
                  <tr key={i} className="border-b border-borda last:border-0">
                    {mapeamento.colunas_disponiveis.map((c) => (
                      <td key={c} className="px-2 py-1 text-foreground">{String(linha[c] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select
              rotulo="Coluna de data"
              opcoes={[{ valor: "", rotulo: "Selecione..." }, ...mapeamento.colunas_disponiveis.map((c) => ({ valor: c, rotulo: c }))]}
              value={colData}
              onChange={(e) => setColData(e.target.value)}
            />
            <Select
              rotulo="Coluna de valor"
              opcoes={[{ valor: "", rotulo: "Selecione..." }, ...mapeamento.colunas_disponiveis.map((c) => ({ valor: c, rotulo: c }))]}
              value={colValor}
              onChange={(e) => setColValor(e.target.value)}
            />
            <Select
              rotulo="Coluna de descrição"
              opcoes={[{ valor: "", rotulo: "Selecione..." }, ...mapeamento.colunas_disponiveis.map((c) => ({ valor: c, rotulo: c }))]}
              value={colDescricao}
              onChange={(e) => setColDescricao(e.target.value)}
            />
            <Input rotulo="Delimitador" value={delimitador} onChange={(e) => setDelimitador(e.target.value)} />
            <Input rotulo="Codificação" value={encoding} onChange={(e) => setEncoding(e.target.value)} />
            <Select
              rotulo="Coluna de Tipo (opcional)"
              opcoes={[{ valor: "", rotulo: "(nenhuma)" }, ...mapeamento.colunas_disponiveis.map((c) => ({ valor: c, rotulo: c }))]}
              value={colTipo}
              onChange={(e) => selecionarColunaTipo(e.target.value)}
            />
          </div>

          {colTipo ? (
            <div className="flex flex-col gap-3 rounded-lg border border-borda p-3">
              <p className="text-sm font-medium text-foreground">
                O que cada valor da coluna &quot;{colTipo}&quot; representa?
              </p>
              {valoresDistintosTipo.length === 0 ? (
                <p className="text-xs text-muted">
                  Nenhum valor encontrado na amostra desta coluna.
                </p>
              ) : (
                valoresDistintosTipo.map((valorBruto) => (
                  <Select
                    key={valorBruto}
                    rotulo={`Valor "${valorBruto}" representa`}
                    opcoes={[
                      { valor: "receita", rotulo: "Receita" },
                      { valor: "despesa", rotulo: "Despesa" },
                      { valor: "", rotulo: "Não importar (transferência/outro)" },
                    ]}
                    value={mapeamentoTipo[valorBruto] ?? ""}
                    onChange={(e) =>
                      setMapeamentoTipo((atual) => ({
                        ...atual,
                        [valorBruto]: e.target.value as "receita" | "despesa" | "",
                      }))
                    }
                  />
                ))
              )}
              <p className="text-xs text-muted">
                Valores fora da amostra acima (se houver) ficarão marcados como &quot;Precisam de
                revisão&quot; e podem ter o tipo definido manualmente na etapa de revisão.
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted">
              O tipo (receita/despesa) é inferido pelo sinal do valor (positivo = receita, negativo
              = despesa); ajuste manualmente na etapa de revisão se necessário.
            </p>
          )}

          <Button onClick={confirmarMapeamento} carregando={carregando} disabled={!colData || !colValor || !colDescricao}>
            Pré-visualizar
          </Button>
        </Card>
      )}

      {etapa === 2 && previa && (
        <div className="flex flex-col gap-4">
          {previa.saldo && (
            <Card className="flex items-center gap-3 text-sm">
              <AlertTriangle size={18} className="text-muted" />
              <div>
                <p className="text-foreground">
                  Saldo informado pelo banco em {formatarData(previa.saldo.data_saldo)}:{" "}
                  <Money valor={previa.saldo.saldo_banco} className="font-medium" />
                  {" — saldo calculado pelo app: "}
                  <Money valor={previa.saldo.saldo_aplicativo} className="font-medium" />
                </p>
                <p className="text-muted">
                  Diferença: <Money valor={previa.saldo.diferenca} />
                </p>
              </div>
            </Card>
          )}

          <Card className="flex flex-col gap-3">
            <p className="text-sm text-muted">
              Lemos <strong>{previa.total_lidas}</strong> linha(s) do arquivo. Veja o resumo antes
              de revisar cada uma:
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg bg-receita-fundo p-3 text-center">
                <p className="text-2xl font-semibold text-receita-texto">{contagemPorStatus.ok}</p>
                <p className="text-xs text-receita-texto">Prontas para importar</p>
              </div>
              <div className="rounded-lg bg-fatura-fundo p-3 text-center">
                <p className="text-2xl font-semibold text-fatura-texto">{contagemPorStatus.duplicada}</p>
                <p className="text-xs text-fatura-texto">Possível duplicidade</p>
              </div>
              <div className="rounded-lg bg-transferencia-fundo p-3 text-center">
                <p className="text-2xl font-semibold text-transferencia-texto">{contagemPorStatus.revisar}</p>
                <p className="text-xs text-transferencia-texto">Precisam de revisão</p>
              </div>
              <div className="rounded-lg bg-despesa-fundo p-3 text-center">
                <p className="text-2xl font-semibold text-despesa-texto">{contagemPorStatus.erro}</p>
                <p className="text-xs text-despesa-texto">Com erro</p>
              </div>
            </div>
          </Card>

          <div className="flex items-center justify-between">
            <Button variante="secundaria" onClick={reiniciar}>
              Cancelar
            </Button>
            <Button onClick={() => setEtapa(3)}>Continuar para revisão</Button>
          </div>
        </div>
      )}

      {etapa === 3 && previa && (
        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-3">
            <p className="text-sm text-muted">
              Revise cada linha. Desmarque o que não deve ser importado; marque como transferência
              ou pagamento de fatura quando aplicável.
            </p>
            <div className="flex flex-col divide-y divide-borda">
              {previa.linhas.map((linha) => (
                <LinhaRevisaoItem
                  key={linha.indice}
                  linha={linha}
                  revisao={revisao.get(linha.indice)}
                  contas={contas ?? []}
                  cartoes={cartoes ?? []}
                  categorias={categorias ?? []}
                  contaOrigemId={contaId}
                  onAtualizar={(campos) => atualizarLinha(linha.indice, campos)}
                />
              ))}
            </div>
          </Card>

          <div className="flex items-center justify-between">
            <Button variante="secundaria" onClick={() => setEtapa(2)}>
              Voltar
            </Button>
            <Button onClick={confirmarImportacao} carregando={carregando} disabled={quantidadeIncluida === 0}>
              Confirmar importação ({quantidadeIncluida})
            </Button>
          </div>
        </div>
      )}

      {etapa === 4 && resultado && (
        <Card className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-receita-fundo p-3 text-center">
              <p className="text-2xl font-semibold text-receita-texto">{resultado.importadas}</p>
              <p className="text-xs text-receita-texto">Importados</p>
            </div>
            <div className="rounded-lg border border-borda p-3 text-center">
              <p className="text-2xl font-semibold text-foreground">{quantidadeIgnorada}</p>
              <p className="text-xs text-muted">Ignorados</p>
            </div>
            <div className="rounded-lg bg-fatura-fundo p-3 text-center">
              <p className="text-2xl font-semibold text-fatura-texto">{contagemPorStatus.duplicada}</p>
              <p className="text-xs text-fatura-texto">Duplicados sinalizados</p>
            </div>
            <div className="rounded-lg bg-despesa-fundo p-3 text-center">
              <p className="text-2xl font-semibold text-despesa-texto">{resultado.com_erro.length}</p>
              <p className="text-xs text-despesa-texto">Com erro</p>
            </div>
          </div>
          <p className="text-foreground">
            Importação concluída: <strong>{resultado.importadas}</strong> de{" "}
            <strong>{resultado.total}</strong> linha(s) importada(s).
          </p>
          {resultado.com_erro.length > 0 && (
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-despesa-texto">
                {resultado.com_erro.length} linha(s) não puderam ser importadas:
              </p>
              {resultado.com_erro.map((e) => (
                <p key={e.indice} className="text-sm text-muted">
                  {e.descricao}: {e.motivo}
                </p>
              ))}
            </div>
          )}
          <Button onClick={reiniciar}>Nova importação</Button>
        </Card>
      )}
    </div>
  );
}

function LinhaRevisaoItem({
  linha,
  revisao,
  contas,
  cartoes,
  categorias,
  contaOrigemId,
  onAtualizar,
}: {
  linha: LinhaPrevia;
  revisao: LinhaRevisao | undefined;
  contas: Array<{ id: number; nome: string }>;
  cartoes: Array<{ id: number; nome: string }>;
  categorias: Array<{ id: number; nome: string; tipo: string }>;
  contaOrigemId: number | null;
  onAtualizar: (campos: Partial<LinhaRevisao>) => void;
}) {
  if (!revisao) return null;

  if (linha.status === "erro") {
    return (
      <div className="flex items-center gap-2 py-2 text-sm text-despesa-texto">
        <AlertTriangle size={14} />
        {linha.descricao || linha.mensagem} — {linha.mensagem}
      </div>
    );
  }

  const categoriasCompativeis = categorias.filter(
    (c) => c.tipo === "ambos" || c.tipo === revisao.tipo
  );

  return (
    <div className="flex flex-col gap-2 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="checkbox"
          aria-label={`Incluir lançamento "${linha.descricao}"`}
          checked={revisao.incluida}
          onChange={(e) => onAtualizar({ incluida: e.target.checked })}
        />
        <span className="text-sm font-medium text-foreground">{linha.descricao}</span>
        <span className="text-xs text-muted">{formatarData(linha.data)}</span>
        <Money valor={linha.valor} className="text-sm" />
        {linha.status === "duplicada" && <Badge>Possível duplicidade</Badge>}
        {linha.status === "revisar" && <Badge>Defina o tipo</Badge>}
      </div>

      {revisao.incluida && (
        <div className="flex flex-wrap items-center gap-2 pl-6">
          {linha.tipo === null && (
            <Select
              rotulo="Tipo"
              opcoes={[
                { valor: "despesa", rotulo: "Despesa" },
                { valor: "receita", rotulo: "Receita" },
              ]}
              value={revisao.tipo}
              onChange={(e) => onAtualizar({ tipo: e.target.value as "receita" | "despesa" })}
            />
          )}

          {(linha.possivel_transferencia || linha.possivel_pagamento_fatura) && (
            <Select
              rotulo="Classificação"
              opcoes={[
                { valor: "normal", rotulo: "Lançamento comum" },
                ...(linha.possivel_transferencia ? [{ valor: "transferencia", rotulo: "Transferência entre contas" }] : []),
                ...(linha.possivel_pagamento_fatura ? [{ valor: "pagamento_fatura", rotulo: "Pagamento de fatura" }] : []),
              ]}
              value={revisao.classificacao}
              onChange={(e) => onAtualizar({ classificacao: e.target.value as LinhaRevisao["classificacao"] })}
            />
          )}

          {revisao.classificacao === "normal" && (
            <Select
              rotulo="Categoria"
              opcoes={[{ valor: "", rotulo: "Sem categoria" }, ...categoriasCompativeis.map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
              value={revisao.categoriaId !== null ? String(revisao.categoriaId) : ""}
              onChange={(e) => onAtualizar({ categoriaId: e.target.value ? Number(e.target.value) : null })}
            />
          )}

          {revisao.classificacao === "transferencia" && (
            <Select
              rotulo="Outra conta da transferência"
              opcoes={[
                { valor: "", rotulo: "Selecione..." },
                ...contas.filter((c) => c.id !== contaOrigemId).map((c) => ({ valor: String(c.id), rotulo: c.nome })),
              ]}
              value={revisao.outraContaId !== null ? String(revisao.outraContaId) : ""}
              onChange={(e) => onAtualizar({ outraContaId: e.target.value ? Number(e.target.value) : null })}
            />
          )}

          {revisao.classificacao === "pagamento_fatura" && (
            <Select
              rotulo="Cartão da fatura"
              opcoes={[{ valor: "", rotulo: "Selecione..." }, ...cartoes.map((c) => ({ valor: String(c.id), rotulo: c.nome }))]}
              value={revisao.cartaoId !== null ? String(revisao.cartaoId) : ""}
              onChange={(e) => onAtualizar({ cartaoId: e.target.value ? Number(e.target.value) : null })}
            />
          )}
        </div>
      )}
    </div>
  );
}
