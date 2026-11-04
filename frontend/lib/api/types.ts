export type Conta = {
  id: number;
  nome: string;
  tipo: string;
  instituicao: string | null;
  saldo_inicial: string;
  data_saldo_inicial: string | null;
  ativa: boolean;
};

export type Categoria = {
  id: number;
  nome: string;
  tipo: "receita" | "despesa" | "ambos";
  categoria_pai_id: number | null;
  ativa: boolean;
};

export type Transacao = {
  id: number;
  tipo: "receita" | "despesa" | "transferencia";
  descricao: string;
  valor: string;
  data_transacao: string;
  categoria_id: number | null;
  conta_id: number | null;
  cartao_id: number | null;
  fatura_id: number | null;
  conta_destino_id: number | null;
  observacao: string | null;
  origem: string;
  numero_parcela: number | null;
  total_parcelas: number | null;
};

export type Cartao = {
  id: number;
  nome: string;
  instituicao: string | null;
  limite: string;
  dia_fechamento: number;
  dia_vencimento: number;
  conta_pagamento_id: number | null;
  ativo: boolean;
  limite_utilizado: string | null;
  limite_disponivel: string | null;
  fatura_atual: Fatura | null;
};

export type Fatura = {
  id: number;
  cartao_id: number;
  mes_referencia: string;
  data_fechamento: string;
  data_vencimento: string;
  status: string;
  total: string;
  total_pago: string;
  saldo_devedor: string;
  status_exibicao: string;
};

export type Meta = {
  id: number;
  nome: string;
  descricao: string | null;
  valor_alvo: string;
  valor_atual: string;
  data_inicio: string;
  data_limite: string | null;
  concluida: boolean;
  progresso: {
    percentual: string;
    valor_restante: string;
    concluida: boolean;
  };
};

export type CategoriaResumo = {
  categoria_id: number;
  categoria: string;
  tipo: string;
  total: string;
  percentual: string;
};

export type Regra = {
  id: number;
  texto_busca: string;
  operador: "contem" | "comeca_com" | "igual";
  categoria_id: number;
  prioridade: number;
  ativa: boolean;
};

export type Recorrencia = {
  id: number;
  tipo: "receita" | "despesa";
  descricao: string;
  valor: string;
  conta_id: number;
  categoria_id: number | null;
  periodicidade: "mensal" | "semanal" | "anual";
  data_inicio: string;
  data_fim: string | null;
  ativa: boolean;
};

export type CompromissoPrevisto = {
  mes: string;
  parcelas_previstas: string;
  recorrencias_previstas: string;
  faturas_conhecidas: string;
  total_previsto: string;
};

export type GastoForaPadrao = {
  transacao_id: number;
  categoria_id: number;
  categoria: string;
  descricao: string;
  valor: string;
  data_transacao: string;
  faixa_normal_min: string;
  faixa_normal_max: string;
};

export type ResumoDashboard = {
  periodo: { inicio: string; fim: string };
  saldo_total: string;
  saldos_contas: Array<{ conta_id: number; nome: string; ativa: boolean; saldo: string; data_saldo_inicial: string | null }>;
  receitas: string;
  despesas: string;
  resultado: string;
  taxa_economia: string | null;
  cartoes: { total_faturas_abertas: number; total_faturas_a_vencer: number; cartoes: Array<Record<string, unknown>> };
  projecao_mes: {
    despesas_acumuladas: string;
    dias_decorridos: number;
    dias_do_mes: number;
    projecao_fim_mes: string;
    confianca_baixa: boolean;
    mes_passado_total: string;
    media_3_meses: string;
  };
  maiores_receitas: CategoriaResumo[];
  maiores_despesas: CategoriaResumo[];
  insights_principais: string[];
};
