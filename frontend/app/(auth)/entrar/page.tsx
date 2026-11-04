"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { criarClienteNavegador } from "@/lib/supabase/client";

export default function PaginaEntrar() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [emailNaoConfirmado, setEmailNaoConfirmado] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [mensagemReenvio, setMensagemReenvio] = useState<string | null>(null);

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEmailNaoConfirmado(false);
    setMensagemReenvio(null);
    setCarregando(true);

    const supabase = criarClienteNavegador();
    const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
    setCarregando(false);

    if (error) {
      setErro(error.message);
      if (error.message.toLowerCase().includes("confirm")) {
        setEmailNaoConfirmado(true);
      }
      return;
    }
    router.push("/inicio");
    router.refresh();
  }

  async function reenviarConfirmacao() {
    setReenviando(true);
    setMensagemReenvio(null);
    const supabase = criarClienteNavegador();
    await supabase.auth.resend({ type: "signup", email });
    setReenviando(false);
    setMensagemReenvio("Se essa conta existir e ainda não estiver confirmada, enviamos um novo e-mail.");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold text-foreground">Economia UaU</h1>
        <p className="mb-6 text-sm text-muted">Organização financeira pessoal</p>

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
            rotulo="Senha"
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
          {erro && (
            <p role="alert" className="text-sm text-despesa-texto">
              {erro}
            </p>
          )}
          <Button type="submit" carregando={carregando}>
            Entrar
          </Button>
        </form>

        {emailNaoConfirmado && (
          <div className="mt-3 rounded-lg border border-borda p-3 text-sm">
            <p className="mb-2 text-muted">Parece que este e-mail ainda não foi confirmado.</p>
            <Button variante="secundaria" onClick={reenviarConfirmacao} carregando={reenviando}>
              Reenviar e-mail de confirmação
            </Button>
            {mensagemReenvio && <p className="mt-2 text-receita-texto">{mensagemReenvio}</p>}
          </div>
        )}

        <div className="mt-4 flex justify-between text-sm">
          <Link href="/criar-conta" className="text-primaria hover:underline">
            Criar conta
          </Link>
          <Link href="/esqueci-senha" className="text-primaria hover:underline">
            Esqueci a senha
          </Link>
        </div>
      </div>
    </div>
  );
}
