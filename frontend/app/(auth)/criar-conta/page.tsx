"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { criarClienteNavegador } from "@/lib/supabase/client";

export default function PaginaCriarConta() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSucesso(null);

    if (senha !== confirmarSenha) {
      setErro("As senhas não coincidem.");
      return;
    }
    if (senha.length < 6) {
      setErro("A senha deve ter ao menos 6 caracteres.");
      return;
    }

    setCarregando(true);
    const supabase = criarClienteNavegador();
    const { data, error } = await supabase.auth.signUp({
      email,
      password: senha,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    setCarregando(false);

    if (error) {
      setErro(error.message);
      return;
    }
    if (data.session) {
      window.location.href = "/inicio";
      return;
    }
    setSucesso("Conta criada. Verifique seu e-mail para confirmar o cadastro antes de entrar.");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold text-foreground">Criar conta</h1>
        <p className="mb-6 text-sm text-muted">Comece a organizar suas finanças.</p>

        <form onSubmit={aoSubmeter} className="flex flex-col gap-4" noValidate>
          <Input
            rotulo="E-mail"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            rotulo="Senha (mín. 6 caracteres)"
            type="password"
            autoComplete="new-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
          <Input
            rotulo="Confirmar senha"
            type="password"
            autoComplete="new-password"
            required
            value={confirmarSenha}
            onChange={(e) => setConfirmarSenha(e.target.value)}
          />
          {erro && (
            <p role="alert" className="text-sm text-despesa-texto">
              {erro}
            </p>
          )}
          {sucesso && <p className="text-sm text-receita-texto">{sucesso}</p>}
          <Button type="submit" carregando={carregando}>
            Criar conta
          </Button>
        </form>

        <div className="mt-4 text-sm">
          <Link href="/entrar" className="text-primaria hover:underline">
            Já tenho conta — entrar
          </Link>
        </div>
      </div>
    </div>
  );
}
