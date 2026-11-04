/** Formatação padronizada (Parte 24): moeda em R$ 1.234,56, data em
 * dd/mm/aaaa, percentual em 27,4%. Sempre pt-BR, nunca depende do locale
 * do navegador do usuário. */

// Monta "R$ 1.234,56" manualmente (sinal + "R$ " + número) em vez de usar
// style:"currency" do Intl — o ICU insere um espaço NÃO separável (U+00A0)
// entre "R$" e o número, diferente do espaço comum usado por
// finance_app/src/formatacao.py:formatar_moeda no Streamlit. Montar à mão
// garante o mesmo texto literal nas duas interfaces.
const FORMATADOR_NUMERO_MOEDA = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const FORMATADOR_PERCENTUAL = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const FORMATADOR_DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "America/Sao_Paulo",
});

export function formatarMoeda(valor: number | string): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return "—";
  const sinal = numero < 0 ? "-" : "";
  return `${sinal}R$ ${FORMATADOR_NUMERO_MOEDA.format(Math.abs(numero))}`;
}

export function formatarPercentual(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return "—";
  return `${FORMATADOR_PERCENTUAL.format(numero)}%`;
}

/** Aceita "2026-10-07" (ISO, como vem da API) ou um objeto Date. */
export function formatarData(valor: string | Date | null | undefined): string {
  if (!valor) return "—";
  const data = typeof valor === "string" ? new Date(`${valor}T00:00:00`) : valor;
  if (Number.isNaN(data.getTime())) return "—";
  return FORMATADOR_DATA.format(data);
}

export function formatarMes(valor: string | Date | null | undefined): string {
  if (!valor) return "—";
  const data = typeof valor === "string" ? new Date(`${valor}T00:00:00`) : valor;
  if (Number.isNaN(data.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", { month: "2-digit", year: "numeric" }).format(data);
}
