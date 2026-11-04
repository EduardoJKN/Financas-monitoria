import { NextResponse } from "next/server";

import { criarClienteServidor } from "@/lib/supabase/server";

/** Destino dos links de confirmação de e-mail / recuperação de senha
 * (Parte 8) — troca o "code" da URL por uma sessão via cookies e manda o
 * usuário para onde precisa ir a seguir. */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const proximo = searchParams.get("next") ?? "/inicio";

  if (code) {
    const supabase = await criarClienteServidor();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${proximo}`);
    }
  }

  return NextResponse.redirect(`${origin}/entrar`);
}
