import { expect, test } from "@playwright/test";

test("redireciona para /entrar quando não autenticado", async ({ page }) => {
  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/entrar/);
});

test("tela de login mostra e-mail, senha e os links de navegação", async ({ page }) => {
  await page.goto("/entrar");
  await expect(page.getByLabel("E-mail")).toBeVisible();
  await expect(page.getByLabel("Senha")).toBeVisible();
  await expect(page.getByRole("link", { name: "Criar conta" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Esqueci a senha" })).toBeVisible();
});

test("tela de login funciona em viewport mobile (390px)", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/entrar");
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
});

for (const rota of ["/regras", "/recorrencias", "/compromissos"]) {
  test(`${rota} também redireciona para /entrar quando não autenticado`, async ({ page }) => {
    await page.goto(rota);
    await expect(page).toHaveURL(/\/entrar/);
  });
}
