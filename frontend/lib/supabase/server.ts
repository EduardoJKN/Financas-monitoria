import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Cliente Supabase para uso em Server Components/Route Handlers — lê e
 * escreve a sessão via cookies HTTP-only (padrão recomendado do
 * @supabase/ssr). Mesma publishable key do cliente de navegador; nada
 * privado aqui também.
 */
export async function criarClienteServidor() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesParaDefinir) {
          try {
            cookiesParaDefinir.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // chamado de um Server Component sem permissão de escrita de
            // cookie — ignorado de propósito; o middleware já cuida da
            // renovação de sessão nessas requisições.
          }
        },
      },
    }
  );
}
