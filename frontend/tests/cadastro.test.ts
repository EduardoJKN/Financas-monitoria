import type { AuthError, Session, User } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";

import { interpretarResultadoCadastro } from "@/lib/auth/cadastro";

describe("interpretarResultadoCadastro", () => {
  it("retorna sessaoCriada quando o signUp já devolve uma sessão", () => {
    const resultado = interpretarResultadoCadastro(
      {
        user: { id: "1", identities: [{ id: "x" }] } as unknown as User,
        session: { access_token: "t" } as unknown as Session,
      },
      null
    );
    expect(resultado).toEqual({ tipo: "sessaoCriada" });
  });

  it("retorna confirmacaoPendente quando há identities novas e nenhuma sessão", () => {
    const resultado = interpretarResultadoCadastro(
      { user: { id: "1", identities: [{ id: "x" }] } as unknown as User, session: null },
      null
    );
    expect(resultado).toEqual({ tipo: "confirmacaoPendente" });
  });

  it("retorna ambiguo quando identities vem vazio (resposta obfuscada do Supabase)", () => {
    const resultado = interpretarResultadoCadastro(
      { user: { id: "1", identities: [] } as unknown as User, session: null },
      null
    );
    expect(resultado).toEqual({ tipo: "ambiguo" });
  });

  it("retorna ambiguo quando identities não vem definido", () => {
    const resultado = interpretarResultadoCadastro(
      { user: { id: "1" } as unknown as User, session: null },
      null
    );
    expect(resultado).toEqual({ tipo: "ambiguo" });
  });

  it("retorna ambiguo quando não há usuário nem sessão nem erro", () => {
    const resultado = interpretarResultadoCadastro(null, null);
    expect(resultado).toEqual({ tipo: "ambiguo" });
  });

  it("retorna emailJaCadastrado para o código oficial email_exists", () => {
    const resultado = interpretarResultadoCadastro(
      null,
      {
        name: "AuthApiError",
        message: "User already registered",
        code: "email_exists",
      } as unknown as AuthError
    );
    expect(resultado).toEqual({ tipo: "emailJaCadastrado" });
  });

  it("retorna emailJaCadastrado para o código oficial user_already_exists", () => {
    const resultado = interpretarResultadoCadastro(
      null,
      {
        name: "AuthApiError",
        message: "User already registered",
        code: "user_already_exists",
      } as unknown as AuthError
    );
    expect(resultado).toEqual({ tipo: "emailJaCadastrado" });
  });

  it("retorna erro para falhas reais de rede/API sem código de duplicidade", () => {
    const resultado = interpretarResultadoCadastro(
      null,
      {
        name: "AuthRetryableFetchError",
        message: "Network request failed",
        code: undefined,
      } as unknown as AuthError
    );
    expect(resultado).toEqual({ tipo: "erro", mensagem: "Network request failed" });
  });
});
