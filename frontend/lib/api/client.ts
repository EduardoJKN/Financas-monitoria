import { criarClienteNavegador } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ErroApi extends Error {
  status: number;

  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.status = status;
  }
}

/**
 * Camada única de acesso à API (Parte 9) — nenhum componente deve usar
 * `fetch` diretamente. Responsabilidades: obter o access_token atual (e
 * renovar a sessão quando necessário, via o próprio cliente Supabase),
 * anexar Authorization: Bearer, padronizar erros e tipar request/response.
 */
async function obterAccessToken(): Promise<string | null> {
  const supabase = criarClienteNavegador();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

type Opcoes = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
};

function montarQueryString(params?: Opcoes["params"]): string {
  if (!params) return "";
  const entradas = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entradas.length === 0) return "";
  const busca = new URLSearchParams();
  entradas.forEach(([chave, valor]) => busca.set(chave, String(valor)));
  return `?${busca.toString()}`;
}

export async function apiFetch<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const token = await obterAccessToken();

  const resposta = await fetch(`${API_URL}${caminho}${montarQueryString(opcoes.params)}`, {
    method: opcoes.method ?? "GET",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opcoes.body ? { "Content-Type": "application/json" } : {}),
    },
    body: opcoes.body ? JSON.stringify(opcoes.body) : undefined,
    signal: opcoes.signal,
  });

  if (resposta.status === 401) {
    // Sessão inválida/expirada mesmo após o middleware tentar renovar —
    // força novo login em vez de seguir mostrando dados potencialmente
    // incorretos.
    if (typeof window !== "undefined") {
      window.location.href = "/entrar";
    }
    throw new ErroApi(401, "Sessão expirada. Faça login novamente.");
  }

  if (resposta.status === 204) {
    return undefined as T;
  }

  const corpo = await resposta.json().catch(() => null);

  if (!resposta.ok) {
    const mensagem =
      (corpo && typeof corpo === "object" && "detail" in corpo && String(corpo.detail)) ||
      "Não foi possível completar a operação.";
    throw new ErroApi(resposta.status, mensagem);
  }

  return corpo as T;
}

export async function apiUpload<T>(caminho: string, formData: FormData): Promise<T> {
  const token = await obterAccessToken();
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  });

  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const mensagem =
      (corpo && typeof corpo === "object" && "detail" in corpo && String(corpo.detail)) ||
      "Não foi possível completar o envio do arquivo.";
    throw new ErroApi(resposta.status, mensagem);
  }
  return corpo as T;
}
