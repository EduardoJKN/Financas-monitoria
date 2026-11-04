import { describe, expect, it } from "vitest";

import { formatarData, formatarMoeda, formatarPercentual } from "@/lib/utils/formatadores";

describe("formatarMoeda", () => {
  it("formata valores positivos em R$ 1.234,56", () => {
    expect(formatarMoeda(1234.56)).toBe("R$ 1.234,56");
  });

  it("formata valores negativos", () => {
    expect(formatarMoeda(-85.9)).toBe("-R$ 85,90");
  });

  it("aceita string numérica", () => {
    expect(formatarMoeda("100.00")).toBe("R$ 100,00");
  });

  it("retorna — para valor inválido", () => {
    expect(formatarMoeda("abc")).toBe("—");
  });
});

describe("formatarPercentual", () => {
  it("formata com uma casa decimal e símbolo %", () => {
    expect(formatarPercentual(27.42)).toBe("27,4%");
  });

  it("retorna — para null/undefined", () => {
    expect(formatarPercentual(null)).toBe("—");
    expect(formatarPercentual(undefined)).toBe("—");
  });
});

describe("formatarData", () => {
  it("formata data ISO em dd/mm/aaaa", () => {
    expect(formatarData("2026-10-07")).toBe("07/10/2026");
  });

  it("retorna — para valor vazio", () => {
    expect(formatarData(null)).toBe("—");
    expect(formatarData("")).toBe("—");
  });
});
