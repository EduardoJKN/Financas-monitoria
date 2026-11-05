import { criarClienteNavegador } from "@/lib/supabase/client";

export async function reenviarConfirmacaoDeCadastro(email: string) {
  const supabase = criarClienteNavegador();
  return supabase.auth.resend({ type: "signup", email });
}
