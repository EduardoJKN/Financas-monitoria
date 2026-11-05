"use client";

import { CircleAlert, CircleHelp, MailCheck } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { interpretarResultadoCadastro, type ResultadoCadastro } from "@/lib/auth/cadastro";
import { reenviarConfirmacaoDeCadastro } from "@/lib/auth/reenviarConfirmacao";
import { criarClienteNavegador } from "@/lib/supabase/client";

type ResultadoComCard = Extract<
  ResultadoCadastro,
  { tipo: "emailJaCadastrado" | "confirmacaoPendente" | "ambiguo" }
>;

type AcaoLink = { tipo: "link"; rotulo: string; href: string };
type AcaoReenvio = { tipo: "reenvio"; rotulo: string };

const CLASSE_LINK_SECUNDARIO =
  "inline-flex items-center justify-center rounded-lg border border-borda bg-superficie px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-borda/40";

const CARTAO_POR_TIPO: Record<
  ResultadoComCard["tipo"],
  { Icone: typeof CircleAlert; titulo: string; acoes: (AcaoLink | AcaoReenvio)[] }
> = {
  emailJaCadastrado: {
    Icone: CircleAlert,
    titulo: "Este e-mail já possui cadastro.",
    acoes: [
      { tipo: "link", rotulo: "Entrar", href: "/entrar" },
      { tipo: "link", rotulo: "Esqueci minha senha", href: "/esqueci-senha" },
    ],
  },
  confirmacaoPendente: {
    Icone: MailCheck,
    titulo: "Cadastro realizado. Enviamos um e-mail para confirmar sua conta.",
    acoes: [
      { tipo: "reenvio", rotulo: "Reenviar confirmação" },
      { tipo: "link", rotulo: "Ir para entrar", href: "/entrar" },
    ],
  },
  ambiguo: {
    Icone: CircleHelp,
    titulo:
      "Verifique sua caixa de entrada. Se este e-mail já possuir cadastro, você pode entrar normalmente ou recuperar sua senha.",
    acoes: [
      { tipo: "link", rotulo: "Entrar", href: "/entrar" },
      { tipo: "link", rotulo: "Esqueci minha senha", href: "/esqueci-senha" },
      { tipo: "reenvio", rotulo: "Reenviar confirmação" },
    ],
  },
};

export default function PaginaCriarConta() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoComCard | null>(null);
  const [reenviando, setReenviando] = useState(false);
  const [mensagemReenvio, setMensagemReenvio] = useState<string | null>(null);

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
    const { data, error } = await supabase.auth.signUp({
      email,
      password: senha,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    setCarregando(false);

    const resultadoCadastro = interpretarResultadoCadastro(data, error);

    if (resultadoCadastro.tipo === "erro") {
      setErro(resultadoCadastro.mensagem);
      return;
    }
    if (resultadoCadastro.tipo === "sessaoCriada") {
      window.location.href = "/inicio";
      return;
    }
    setResultado(resultadoCadastro);
  }

  async function aoReenviarConfirmacao() {
    setReenviando(true);
    setMensagemReenvio(null);
    await reenviarConfirmacaoDeCadastro(email);
    setReenviando(false);
    setMensagemReenvio("Se essa conta existir e ainda não estiver confirmada, enviamos um novo e-mail.");
  }

  if (resultado) {
    const { Icone, titulo, acoes } = CARTAO_POR_TIPO[resultado.tipo];
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <Card className="flex flex-col gap-4">
            <div role="status" className="flex items-start gap-3">
              <Icone className="mt-0.5 h-6 w-6 shrink-0 text-primaria" aria-hidden="true" />
              <p className="text-sm text-foreground">{titulo}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              {acoes.map((acao) =>
                acao.tipo === "link" ? (
                  <Link key={acao.rotulo} href={acao.href} className={CLASSE_LINK_SECUNDARIO}>
                    {acao.rotulo}
                  </Link>
                ) : (
                  <Button
                    key={acao.rotulo}
                    variante="secundaria"
                    onClick={aoReenviarConfirmacao}
                    carregando={reenviando}
                  >
                    {acao.rotulo}
                  </Button>
                )
              )}
            </div>

            {mensagemReenvio && <p className="text-sm text-receita-texto">{mensagemReenvio}</p>}
          </Card>
        </div>
      </div>
    );
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
