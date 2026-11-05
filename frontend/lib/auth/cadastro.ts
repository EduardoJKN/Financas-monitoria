import type { AuthError, Session, User } from "@supabase/supabase-js";

export type ResultadoCadastro =
  | { tipo: "sessaoCriada" }
  | { tipo: "emailJaCadastrado" }
  | { tipo: "confirmacaoPendente" }
  | { tipo: "ambiguo" }
  | { tipo: "erro"; mensagem: string };

type DadosSignUp = { user: User | null; session: Session | null } | null | undefined;

/** Códigos oficiais do GoTrue para e-mail/usuário já cadastrado (@supabase/auth-js/src/lib/error-codes.ts). */
const CODIGOS_EMAIL_JA_CADASTRADO = new Set(["email_exists", "user_already_exists"]);

/**
 * Interpreta a resposta de `supabase.auth.signUp()` sem nunca afirmar que uma
 * conta nova foi criada quando a resposta é ambígua: com "Confirm email" e
 * "Confirm phone" habilitados, o Supabase devolve propositalmente um usuário
 * obfuscado (sem erro, sem sessão, `identities: []`) para um e-mail já
 * cadastrado, a fim de não permitir enumeração — esse caso cai em `ambiguo`.
 */
export function interpretarResultadoCadastro(
  data: DadosSignUp,
  error: AuthError | null | undefined
): ResultadoCadastro {
  if (error) {
    const codigo = error.code;
    const mensagem = error.message?.toLowerCase() ?? "";
    if ((codigo && CODIGOS_EMAIL_JA_CADASTRADO.has(codigo)) || mensagem.includes("already registered")) {
      return { tipo: "emailJaCadastrado" };
    }
    return { tipo: "erro", mensagem: error.message };
  }

  if (data?.session) {
    return { tipo: "sessaoCriada" };
  }

  const identidades = data?.user?.identities;
  if (identidades && identidades.length > 0) {
    return { tipo: "confirmacaoPendente" };
  }

  return { tipo: "ambiguo" };
}
