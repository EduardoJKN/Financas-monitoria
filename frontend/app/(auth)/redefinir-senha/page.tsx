"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { criarClienteNavegador } from "@/lib/supabase/client";

export default function PaginaRedefinirSenha() {
  const router = useRouter();
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

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
    const { error } = await supabase.auth.updateUser({ password: senha });
    setCarregando(false);

    if (error) {
      setErro(error.message);
      return;
    }
    router.push("/inicio");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold text-foreground">Nova senha</h1>
        <p className="mb-6 text-sm text-muted">Escolha uma nova senha para sua conta.</p>

        <form onSubmit={aoSubmeter} className="flex flex-col gap-4" noValidate>
          <Input
            rotulo="Nova senha"
            type="password"
            autoComplete="new-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
          <Input
            rotulo="Confirmar nova senha"
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
          <Button type="submit" carregando={carregando}>
            Salvar nova senha
          </Button>
        </form>
      </div>
    </div>
  );
}
