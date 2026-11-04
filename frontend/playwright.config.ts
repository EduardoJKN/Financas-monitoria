import { defineConfig, devices } from "@playwright/test";

/** E2E (Parte 31). Não depende de usuários reais no Supabase: os cenários
 * cobertos aqui testam proteção de rota (middleware) e renderização da
 * tela de login, que não exigem autenticação real. Cenários que exigem
 * login de verdade (dashboard, lançamento) ficam documentados como
 * pendentes em PARIDADE_MIGRACAO.md — criar um usuário de teste
 * descartável no Supabase real e depois tentar removê-lo sem
 * service_role deixaria resíduo, o que as regras deste projeto proíbem. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // Viewport mobile com o motor Chromium (já instalado) em vez do
    // preset "iPhone 13" (que usa WebKit) — evita depender de um segundo
    // navegador só para o teste de layout responsivo.
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
  ],
  webServer: {
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
