"use client";

import type { User } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";

import { criarClienteNavegador } from "@/lib/supabase/client";

type SessaoContexto = {
  usuario: User | null;
  carregando: boolean;
  sair: () => Promise<void>;
};

const Contexto = createContext<SessaoContexto | undefined>(undefined);

/** Fonte única de identidade no frontend: lê a sessão do Supabase Auth e
 * reage a mudanças (login/logout/renovação) em qualquer aba. Ao sair,
 * limpa todo o cache do TanStack Query — nunca deixar dados do usuário
 * anterior visíveis para o próximo login no mesmo navegador (Parte 10). */
export function ProvedorSessao({ children }: { children: React.ReactNode }) {
  const [supabase] = useState(() => criarClienteNavegador());
  const [usuario, setUsuario] = useState<User | null>(null);
  const [carregando, setCarregando] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUsuario(data.user);
      setCarregando(false);
    });

    const { data: inscricao } = supabase.auth.onAuthStateChange((_evento, sessao) => {
      setUsuario(sessao?.user ?? null);
    });

    return () => inscricao.subscription.unsubscribe();
  }, [supabase]);

  async function sair() {
    await supabase.auth.signOut();
    queryClient.clear();
    window.location.href = "/entrar";
  }

  return <Contexto.Provider value={{ usuario, carregando, sair }}>{children}</Contexto.Provider>;
}

export function useSessao(): SessaoContexto {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useSessao precisa ser usado dentro de <ProvedorSessao>.");
  }
  return contexto;
}
