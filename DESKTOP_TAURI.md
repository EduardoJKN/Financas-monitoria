# Aplicativo desktop (Windows) — caminho via Tauri

**Status desta rodada**: Rust/Cargo não estão instalados neste ambiente
(`rustc`/`cargo` não encontrados no PATH). Por instrução explícita, nenhum
toolchain de sistema foi instalado automaticamente. Este documento descreve
exatamente o que fazer quando alguém (com autorização) quiser gerar o `.exe`.

PWA continua sendo a prioridade — instalável via Chrome/Edge em Windows, "Adicionar
à tela inicial" em Android/iOS, sem nenhuma dependência nova. Tauri é um passo
**opcional**, posterior, só para quem quiser um executável Windows nativo (ícone na
área de trabalho, sem depender do navegador ter o PWA instalado).

## Por que Tauri (e não Electron)

- Empacota o **mesmo build do Next.js já existente** (`frontend/`) — não duplica UI.
- Binário final é ordens de magnitude menor que Electron (usa o WebView2 que já vem
  no Windows 10/11, não embarca um Chromium inteiro).
- Processo Rust do lado nativo é opcional: para esta primeira versão, o app Tauri é
  só uma casca (shell) que carrega a URL do frontend — nenhuma lógica financeira
  precisa ser escrita em Rust.

## Arquitetura proposta

```
Tauri (shell nativo Windows)
   └─ WebView2 aponta para o frontend Next.js já existente
         └─ frontend/ fala com FastAPI (backend/) via HTTP, exatamente como no navegador
               └─ FastAPI fala com Supabase (Postgres + Auth + RLS), inalterado
```

Nenhum código do `frontend/` ou `backend/` muda. O Tauri não substitui o Next.js —
ele só abre uma janela nativa apontando para ele (em produção, para a URL do deploy;
em desenvolvimento, para `http://localhost:3000`).

Duas formas de rodar, igual a qualquer app Tauri:

1. **Desenvolvimento**: a janela Tauri aponta para `http://localhost:3000` (o `next dev`
   já em uso). Útil para testar a "casca" nativa sem rebuildar o frontend a cada mudança.
2. **Produção (gerar o `.exe`)**: `next build && next export`-equivalente (ou o adapter
   de produção do Next) gera os arquivos estáticos/servidos, embutidos no instalador.
   Como o frontend atual usa Server Components/rotas dinâmicas (não é 100% estático),
   a forma recomendada é apontar o Tauri para um Next.js rodando em modo `next start`
   (processo Node empacotado junto, ou servido remotamente) — não para `next export`
   puro, que exigiria tornar o app inteiro estático (perderia SSR).

## Pré-requisitos (não instalados nesta rodada)

1. **Rust** (via [rustup](https://rustup.rs/)) — toolchain `stable-x86_64-pc-windows-msvc`.
2. **Microsoft C++ Build Tools** (Visual Studio Installer → "Desktop development with C++")
   — exigido pelo Rust no Windows.
3. **WebView2 Runtime** — já vem pré-instalado no Windows 10 (atualizado)/11; só
   relevante para Windows mais antigo.
4. **Tauri CLI**: `cargo install tauri-cli` (ou `npm install -D @tauri-apps/cli` dentro
   de `frontend/`, forma recomendada para manter tudo versionado no `package.json`).

Verificação após instalar:

```powershell
rustc --version
cargo --version
```

## Passos para criar o scaffold (quando Rust estiver disponível)

Executar dentro de `frontend/` (reaproveita o mesmo projeto Next.js, não cria um
diretório irmão novo):

```powershell
cd frontend
npm install -D @tauri-apps/cli
npx tauri init
```

Durante o `tauri init`, responder:

- **App name**: `Economia UaU`
- **Window title**: `Economia UaU`
- **Web assets location**: apontar para a pasta de build do Next (`.next` não serve
  direto — ver nota acima sobre SSR; em desenvolvimento, apontar `devPath` para
  `http://localhost:3000`)
- **Dev server URL**: `http://localhost:3000`
- **Dev command**: `npm run dev`
- **Build command**: `npm run build`

Isso cria `frontend/src-tauri/` (projeto Rust mínimo — `tauri.conf.json`, `Cargo.toml`,
`src/main.rs` gerado pelo CLI, sem lógica custom necessária para a v1).

## Configuração mínima esperada (`src-tauri/tauri.conf.json`)

```jsonc
{
  "productName": "Economia UaU",
  "identifier": "com.economiauau.app",
  "app": {
    "windows": [
      { "title": "Economia UaU", "width": 1280, "height": 800, "resizable": true }
    ]
  },
  "build": {
    "devUrl": "http://localhost:3000",
    "frontendDist": "../out" // ou URL de produção, ver nota SSR acima
  }
}
```

Reaproveitar os ícones já gerados em `frontend/public/icons/` (512/192 + o novo
favicon) como base para os formatos que o Tauri exige (`.ico` para Windows) — o
CLI tem `npx tauri icon <caminho-da-imagem-fonte>` para gerar todos os tamanhos
automaticamente a partir de um único PNG.

## Como gerar o `.exe`

```powershell
cd frontend
npx tauri build
```

Gera `frontend/src-tauri/target/release/bundle/msi/Economia UaU_<versao>_x64_en-US.msi`
(instalador) e um `.exe` standalone em `target/release/`.

## O que NÃO foi feito agora (e por quê)

- Nenhum `cargo install`, `rustup`, ou instalação de Visual Studio Build Tools —
  são mudanças de sistema fora do escopo de autorização automática.
- Nenhum diretório `src-tauri/` foi criado (o `tauri init` precisa do CLI, que
  precisa do Rust instalado primeiro).
- Nenhuma decisão tomada sobre como servir o Next.js em produção dentro do
  bundle (processo Node empacotado vs. apontar para um deploy remoto) — depende
  de onde o backend/frontend forem hospedados, decisão ainda não tomada pelo
  usuário.

## Quando fizer sentido revisitar

Depois que o PWA estiver validado em uso real (instalado, testado em Windows/Android/
iOS) e, idealmente, depois que frontend/backend tiverem um ambiente de deploy
definido — o `devUrl`/`frontendDist` do Tauri muda dependendo disso.
