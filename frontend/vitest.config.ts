import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    exclude: ["e2e/**", "node_modules/**"],
    // "pool: threads" com singleThread evita um problema de spawn dos
    // workers padrão (forks) observado quando o caminho do projeto tem
    // caracteres não-ASCII (acentos/espaços) no Windows.
    pool: "threads",
  },
});
