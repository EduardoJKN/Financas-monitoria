import { describe, expect, it } from "vitest";

import { config } from "@/proxy";

const regex = new RegExp(`^${config.matcher[0]}$`);

describe("matcher do proxy (middleware)", () => {
  it.each([
    ["/sw.js", false],
    ["/manifest.json", false],
    ["/icons/icon-192.png", false],
    ["/favicon.ico", false],
    ["/_next/static/chunk.js", false],
    ["/logo.svg", false],
    ["/entrar", true],
    ["/inicio", true],
    ["/auth/callback", true],
  ])("middleware roda em %s -> %s", (caminho, deveRodar) => {
    expect(regex.test(caminho as string)).toBe(deveRodar);
  });
});
