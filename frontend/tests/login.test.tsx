import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

const signInWithPassword = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  criarClienteNavegador: () => ({
    auth: {
      signInWithPassword,
    },
  }),
}));

import PaginaEntrar from "@/app/(auth)/entrar/page";

describe("PaginaEntrar", () => {
  it("mostra os campos de e-mail e senha", () => {
    render(<PaginaEntrar />);
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
  });

  it("mostra mensagem de erro quando o login falha", async () => {
    signInWithPassword.mockResolvedValueOnce({ error: { message: "Invalid login credentials" } });
    render(<PaginaEntrar />);

    await userEvent.type(screen.getByLabelText("E-mail"), "usuario@exemplo.com");
    await userEvent.type(screen.getByLabelText("Senha"), "senha-errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid login credentials");
    expect(push).not.toHaveBeenCalled();
  });

  it("navega para /inicio quando o login tem sucesso", async () => {
    signInWithPassword.mockResolvedValueOnce({ error: null });
    render(<PaginaEntrar />);

    await userEvent.type(screen.getByLabelText("E-mail"), "usuario@exemplo.com");
    await userEvent.type(screen.getByLabelText("Senha"), "senha-correta");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(push).toHaveBeenCalledWith("/inicio");
  });
});
