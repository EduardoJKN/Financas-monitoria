import { describe, expect, it } from "vitest";

import { paraDecimalApi } from "@/lib/utils/numero";

describe("paraDecimalApi", () => {
  it("converte formato brasileiro com milhar", () => {
    expect(paraDecimalApi("1.234,56")).toBe("1234.56");
  });

  it("converte formato brasileiro simples", () => {
    expect(paraDecimalApi("85,90")).toBe("85.90");
  });

  it("aceita formato internacional já com ponto", () => {
    expect(paraDecimalApi("1234.56")).toBe("1234.56");
  });

  it("converte negativo", () => {
    expect(paraDecimalApi("-85,90")).toBe("-85.90");
  });

  it("converte negativo entre parênteses", () => {
    expect(paraDecimalApi("(85,90)")).toBe("-85.90");
  });

  it("remove prefixo R$", () => {
    expect(paraDecimalApi("R$ 1.234,56")).toBe("1234.56");
  });

  it("levanta erro para texto vazio", () => {
    expect(() => paraDecimalApi("")).toThrow();
  });

  it("levanta erro para texto não numérico", () => {
    expect(() => paraDecimalApi("abc")).toThrow();
  });
});
