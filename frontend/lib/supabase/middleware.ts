import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const ROTAS_PUBLICAS = [
  "/entrar",
  "/criar-conta",
  "/esqueci-senha",
  "/redefinir-senha",
  "/auth/callback",
];

/**
 * Renova a sessão (access_token) a cada requisição — é isto que corrige a
 * limitação do Streamlit (sessão não sobrevivia a um refresh de página).
 * Também protege rotas: sem sessão válida, qualquer página fora da lista
 * pública redireciona para /entrar. Nunca confia em dado de usuário vindo
 * do cliente — só o que o Supabase confirma aqui.
 */
export async function atualizarSessao(request: NextRequest) {
  let respostaSupabase = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesParaDefinir) {
          cookiesParaDefinir.forEach(({ name, value }) => request.cookies.set(name, value));
          respostaSupabase = NextResponse.next({ request });
          cookiesParaDefinir.forEach(({ name, value, options }) =>
            respostaSupabase.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data } = await supabase.auth.getUser();
  const usuario = data.user;

  const caminho = request.nextUrl.pathname;
  const ehRotaPublica = ROTAS_PUBLICAS.some((rota) => caminho.startsWith(rota));

  if (!usuario && !ehRotaPublica) {
    const url = request.nextUrl.clone();
    url.pathname = "/entrar";
    return NextResponse.redirect(url);
  }

  return respostaSupabase;
}
