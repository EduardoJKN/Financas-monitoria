"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { criarClienteNavegador } from "@/lib/supabase/client";

export default function PaginaEsqueciSenha() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [carregando, setCarregando] = useState(false);

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    setCarregando(true);
    const supabase = criarClienteNavegador();
    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/redefinir-senha`,
    });
    setCarregando(false);
    setEnviado(true);
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold text-foreground">Recuperar senha</h1>
        <p className="mb-6 text-sm text-muted">
          Informe seu e-mail cadastrado para receber o link de redefinição.
        </p>

        {enviado ? (
          <p className="text-sm text-receita-texto">
            Se esse e-mail estiver cadastrado, enviamos instruções de redefinição de senha.
          </p>
        ) : (
          <form onSubmit={aoSubmeter} className="flex flex-col gap-4" noValidate>
            <Input
              rotulo="E-mail cadastrado"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button type="submit" carregando={carregando}>
              Enviar e-mail de recuperação
            </Button>
          </form>
        )}

        <div className="mt-4 text-sm">
          <Link href="/entrar" className="text-primaria hover:underline">
            Voltar para o login
          </Link>
        </div>
      </div>
    </div>
  );
}
