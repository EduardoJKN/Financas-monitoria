import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BadgeTipo } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Money } from "@/components/ui/Money";

describe("BadgeTipo", () => {
  it("mostra o rótulo em português para cada tipo", () => {
    render(<BadgeTipo tipo="receita" />);
    expect(screen.getByText("Receita")).toBeInTheDocument();
  });

  it("mostra pagamento de fatura", () => {
    render(<BadgeTipo tipo="pagamento_fatura" />);
    expect(screen.getByText("Pagamento de fatura")).toBeInTheDocument();
  });
});

describe("Button", () => {
  it("chama onClick ao clicar", async () => {
    const aoClicar = vi.fn();
    render(<Button onClick={aoClicar}>Salvar</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    expect(aoClicar).toHaveBeenCalledTimes(1);
  });

  it("fica desabilitado quando carregando", () => {
    render(<Button carregando>Salvar</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  });
});

describe("Money", () => {
  it("formata o valor recebido", () => {
    render(<Money valor="1234.56" />);
    expect(screen.getByText("R$ 1.234,56")).toBeInTheDocument();
  });

  it("mostra — quando o valor é nulo", () => {
    render(<Money valor={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("mostra título e descrição", () => {
    render(<EmptyState titulo="Nada aqui" descricao="Crie o primeiro item." />);
    expect(screen.getByText("Nada aqui")).toBeInTheDocument();
    expect(screen.getByText("Crie o primeiro item.")).toBeInTheDocument();
  });
});
