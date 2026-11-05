import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const signUp = vi.fn();
const resend = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  criarClienteNavegador: () => ({
    auth: { signUp, resend },
  }),
}));

import PaginaCriarConta from "@/app/(auth)/criar-conta/page";

async function preencherEEnviar() {
  await userEvent.type(screen.getByLabelText("E-mail"), "usuario@exemplo.com");
  await userEvent.type(screen.getByLabelText("Senha (mín. 6 caracteres)"), "senha123");
  await userEvent.type(screen.getByLabelText("Confirmar senha"), "senha123");
  await userEvent.click(screen.getByRole("button", { name: "Criar conta" }));
}

describe("PaginaCriarConta", () => {
  beforeEach(() => {
    signUp.mockReset();
    resend.mockReset();
  });

  it("mostra erro quando as senhas não coincidem", async () => {
    render(<PaginaCriarConta />);
    await userEvent.type(screen.getByLabelText("E-mail"), "usuario@exemplo.com");
    await userEvent.type(screen.getByLabelText("Senha (mín. 6 caracteres)"), "senha123");
    await userEvent.type(screen.getByLabelText("Confirmar senha"), "outrasenha");
    await userEvent.click(screen.getByRole("button", { name: "Criar conta" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("As senhas não coincidem.");
    expect(signUp).not.toHaveBeenCalled();
  });

  it("mostra erro quando a senha é muito curta", async () => {
    render(<PaginaCriarConta />);
    await userEvent.type(screen.getByLabelText("E-mail"), "usuario@exemplo.com");
    await userEvent.type(screen.getByLabelText("Senha (mín. 6 caracteres)"), "123");
    await userEvent.type(screen.getByLabelText("Confirmar senha"), "123");
    await userEvent.click(screen.getByRole("button", { name: "Criar conta" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A senha deve ter ao menos 6 caracteres.");
    expect(signUp).not.toHaveBeenCalled();
  });

  it("redireciona para /inicio quando o signUp já devolve sessão (login imediato)", async () => {
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, href: "" },
    });

    signUp.mockResolvedValueOnce({
      data: { user: { id: "1", identities: [{ id: "a" }] }, session: { access_token: "t" } },
      error: null,
    });

    render(<PaginaCriarConta />);
    await preencherEEnviar();

    expect(window.location.href).toBe("/inicio");

    Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  });

  it("mostra cartão de confirmação pendente para cadastro novo sem sessão", async () => {
    signUp.mockResolvedValueOnce({
      data: { user: { id: "1", identities: [{ id: "a" }] }, session: null },
      error: null,
    });

    render(<PaginaCriarConta />);
    await preencherEEnviar();

    expect(
      await screen.findByText("Cadastro realizado. Enviamos um e-mail para confirmar sua conta.")
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para entrar" })).toHaveAttribute("href", "/entrar");
    expect(screen.getByRole("button", { name: "Reenviar confirmação" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Criar conta" })).not.toBeInTheDocument();
    expect(screen.queryByText(/conta criada/i)).not.toBeInTheDocument();
  });

  it("mostra 'Este e-mail já possui cadastro.' quando o Supabase retorna o código email_exists", async () => {
    signUp.mockResolvedValueOnce({
      data: { user: null, session: null },
      error: { name: "AuthApiError", message: "User already registered", code: "email_exists" },
    });

    render(<PaginaCriarConta />);
    await preencherEEnviar();

    expect(await screen.findByText("Este e-mail já possui cadastro.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/entrar");
    expect(screen.getByRole("link", { name: "Esqueci minha senha" })).toHaveAttribute("href", "/esqueci-senha");
    expect(screen.queryByRole("button", { name: "Reenviar confirmação" })).not.toBeInTheDocument();
    expect(resend).not.toHaveBeenCalled();
    expect(screen.queryByText(/conta criada/i)).not.toBeInTheDocument();
  });

  it("mostra mensagem neutra quando a resposta do Supabase é ambígua (identities vazio)", async () => {
    signUp.mockResolvedValueOnce({
      data: { user: { id: "1", identities: [] }, session: null },
      error: null,
    });

    render(<PaginaCriarConta />);
    await preencherEEnviar();

    expect(
      await screen.findByText(
        "Verifique sua caixa de entrada. Se este e-mail já possuir cadastro, você pode entrar normalmente ou recuperar sua senha."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/entrar");
    expect(screen.getByRole("link", { name: "Esqueci minha senha" })).toHaveAttribute("href", "/esqueci-senha");
    expect(screen.getByRole("button", { name: "Reenviar confirmação" })).toBeInTheDocument();
    expect(screen.queryByText(/conta criada/i)).not.toBeInTheDocument();
  });

  it("reenvia a confirmação ao clicar no botão do cartão", async () => {
    signUp.mockResolvedValueOnce({
      data: { user: { id: "1", identities: [] }, session: null },
      error: null,
    });
    resend.mockResolvedValueOnce({ data: {}, error: null });

    render(<PaginaCriarConta />);
    await preencherEEnviar();
    await userEvent.click(await screen.findByRole("button", { name: "Reenviar confirmação" }));

    expect(resend).toHaveBeenCalledWith({ type: "signup", email: "usuario@exemplo.com" });
    expect(
      await screen.findByText("Se essa conta existir e ainda não estiver confirmada, enviamos um novo e-mail.")
    ).toBeInTheDocument();
  });

  it("mostra erro real de rede/API e mantém o formulário para nova tentativa", async () => {
    signUp.mockResolvedValueOnce({
      data: { user: null, session: null },
      error: { name: "AuthRetryableFetchError", message: "Network request failed", code: undefined },
    });

    render(<PaginaCriarConta />);
    await preencherEEnviar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Network request failed");
    expect(screen.getByRole("button", { name: "Criar conta" })).toBeInTheDocument();
  });
});
