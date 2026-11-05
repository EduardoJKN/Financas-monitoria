# Deploy — Economia UaU

Guia único para colocar o Economia UaU em produção. Centraliza tudo que antes
estava espalhado (README, comentários de código, conhecimento do autor) —
veja `README.md` para a visão geral do projeto e `PARIDADE_MIGRACAO.md` para
o estado funcional de cada tela.

Este documento é só documentação: nenhum passo aqui foi executado
automaticamente. Todo deploy, `git push`, criação de conta/serviço externo e
configuração do painel do Supabase é feita manualmente por quem está lendo.

## Arquitetura

```
Next.js (frontend/, Vercel)  ──HTTP + Bearer JWT──▶  FastAPI (backend/, Koyeb)  ──SQL (role app_runtime, RLS)──▶  PostgreSQL (Supabase)
        │                                                                                      ▲
        └──────────────────────── Supabase Auth (cadastro/login/sessão) ─────────────────────┘

Streamlit (finance_app/) ── mesma camada de negócio (src/), import direto ── continua em paralelo, fallback da migração.
```

- O frontend nunca acessa o Postgres diretamente — só fala com a API FastAPI
  (dados financeiros) e com o Supabase Auth (sessão/JWT).
- A API FastAPI reaproveita a camada de negócio de `finance_app/src/` (não
  duplica regra nenhuma) e nunca usa a role administrativa do banco.
- O Streamlit continua existindo e funcionando sozinho; nada neste guia o
  afeta.

## Variáveis de ambiente

### Backend (`backend/.env` em dev, variáveis do serviço no Koyeb em produção)

| Variável | Obrigatória | Uso |
|---|---|---|
| `APP_DATABASE_URL` | Sim | Conexão de **execução**, role `app_runtime` (sem BYPASSRLS, sujeita a RLS). É a única credencial de banco que a API usa para servir requisições. |
| `SUPABASE_URL` | Sim | Busca o JWKS público do projeto para validar o JWT localmente (`app/core/security.py`). Não é segredo. |
| `FRONTEND_URL` | Sim em produção | Origem(ns) aceitas por CORS. Uma URL ou várias separadas por vírgula. Nunca `"*"`. Padrão sem a variável: `http://localhost:3000`. |
| `AMBIENTE` | Recomendada | `production` desliga o header/log de timing por requisição (dev-only). Padrão: `development`. |
| `DATABASE_URL` | Não (reservada) | Role administrativa (DDL, contorna RLS). O backend **não lê essa variável hoje** — só é usada pelo Alembic/migrations de `finance_app/`, roteado manualmente, nunca como variável do serviço Koyeb. |
| `SUPABASE_PUBLISHABLE_KEY` | Não (reservada) | Nenhuma rota atual do backend precisa dela. Documentada só por paralelismo com `finance_app/.env.example`. |

`backend/.env.example` tem os placeholders corretos — nunca copie valores reais para lá.

### Frontend (`frontend/.env.local` em dev, env vars do projeto na Vercel em produção)

| Variável | Uso |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL pública do projeto Supabase. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Chave pública (`sb_publishable_...`), segura no cliente. |
| `NEXT_PUBLIC_API_URL` | URL pública da API FastAPI (Koyeb em produção; `http://localhost:8001` em dev). |

Todas com prefixo `NEXT_PUBLIC_` porque são enviadas ao navegador — **nunca**
coloque aqui `DATABASE_URL`, `APP_DATABASE_URL`, senha de Postgres,
`SUPABASE_SERVICE_ROLE_KEY`/`sb_secret`/`service_role` ou qualquer credencial
privada. O frontend não tem, e não deve ter, nenhuma delas.

### finance_app/ (Streamlit — referência, não faz parte deste deploy)

Usa `DATABASE_URL` (migrations/Alembic) **e** `APP_DATABASE_URL` (runtime),
além de `SUPABASE_PUBLISHABLE_KEY` e `APP_URL`. Ver `finance_app/README.md`.
Continua sendo deployado separadamente (ex.: Streamlit Community Cloud), sem
relação com Vercel/Koyeb.

## Desenvolvimento local

```bash
# Streamlit (porta 8501)
cd finance_app && .venv/Scripts/python.exe -m streamlit run app.py

# FastAPI (porta 8001 — 8000 dá WinError 10013 neste ambiente Windows;
# se 8000 estiver livre na sua máquina, pode usá-la e ajustar
# NEXT_PUBLIC_API_URL em frontend/.env.local de acordo)
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001

# Next.js (porta 3000)
cd frontend && npm run dev
```

O backend precisa ser iniciado de dentro de `backend/` (imports absolutos
`from app....` assumem `backend/` como raiz do `sys.path` — mesma convenção
do Dockerfile e do `pytest.ini`).

## Produção — comando e porta

Comando de produção do backend (compatível com qualquer hospedagem cloud,
já configurado no `Dockerfile`):

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Nunca fixa `8001` (isso é só dev local). `GET /health` responde `200` sem
exigir autenticação (testado em `backend/tests/test_seguranca_api.py` e
validado manualmente neste guia subindo a imagem Docker real).

## Ordem exata do deploy manual

1. Garantir repositório limpo (`git status` sem pendências que você não
   queira versionar).
2. Deploy do FastAPI no Koyeb (seção abaixo).
3. Obter a URL pública da API (`https://<app>.koyeb.app`).
4. Validar `GET https://<app>.koyeb.app/health` → `200 {"status":"ok"}`.
5. Criar o projeto do frontend na Vercel (seção abaixo), **ainda sem**
   `NEXT_PUBLIC_API_URL` definitivo se preferir, ou já com a URL do passo 3.
6. Configurar `NEXT_PUBLIC_API_URL` = URL pública da API (passo 3).
7. Deploy do Next.js.
8. Obter a URL pública do frontend (`https://<app>.vercel.app`).
9. Atualizar `FRONTEND_URL` no Koyeb com essa URL (pode manter
   `http://localhost:3000` junto, separado por vírgula, se quiser continuar
   testando local contra a API de produção).
10. Redeploy/restart do serviço no Koyeb para aplicar a nova `FRONTEND_URL`.
11. Configurar o Supabase Auth (Site URL + Redirect URLs) com a URL do
    passo 8 — seção "Supabase" abaixo.
12. Testar autenticação (cadastro, confirmação de e-mail, login, logout,
    recuperação de senha) na URL pública.
13. Testar operações financeiras (lançamentos, contas, cartões, dashboard).
14. Testar isolamento multiusuário (duas contas reais, cada uma só vê os
    próprios dados).
15. Instalar o PWA (Android/iOS/Windows — seção "PWA" abaixo).
16. Testar no celular.
17. Testar no PC.

## Koyeb (backend)

**Importante — correção em relação ao plano original:** o `Dockerfile` faz
`COPY finance_app ./finance_app` com caminho relativo à **raiz do repositório**
(a API reaproveita `finance_app/src/`, não duplica a regra financeira). A
documentação do Koyeb confirma que, ao definir um *Work directory*, "o
resto do repositório não faz parte do ambiente de build" — ou seja, se o
*Work directory* for `backend`, o build falha porque `finance_app/` não
estaria mais acessível. Por isso:

- **Work directory**: deixe em branco/padrão (raiz do repositório). **Não**
  defina como `backend`.
- **Builder**: Dockerfile.
- **Dockerfile location**: `backend/Dockerfile` (caminho relativo ao Work
  directory, que é a raiz).
- Build/run equivalente ao que foi testado manualmente neste guia:
  `docker build -f backend/Dockerfile .` a partir da raiz do repo.

Demais configurações:

- **Porta**: o serviço escuta em `$PORT` (o `Dockerfile` já usa
  `--port ${PORT:-8000}`); o Koyeb injeta essa variável automaticamente —
  não é preciso declará-la manualmente.
- **Healthcheck**: `GET /health`, porta `$PORT`, sem autenticação.
- **Versão do Python**: fixada na imagem base do `Dockerfile`
  (`python:3.11-slim`) — não há campo separado de versão do Python a
  configurar no Koyeb quando o builder é Dockerfile.
- **Variáveis de ambiente**: `APP_DATABASE_URL`, `SUPABASE_URL`,
  `FRONTEND_URL` (URL da Vercel, obtida no passo 8 do deploy), `AMBIENTE=production`.
- **Instância**: a aplicação usa um cache em memória por processo
  (`app/core/cache.py`, TTL curto, sempre isolado por `usuario_id`). Com 1
  réplica funciona exatamente como testado; se escalar para múltiplas
  réplicas no futuro, cada uma terá seu próprio cache (não é um problema de
  segurança/correção, só reduz um pouco a taxa de acerto do cache) — não
  bloqueante para o primeiro deploy.

## Vercel (frontend)

- **Root Directory**: `frontend`.
- **Framework Preset**: Next.js (auto-detectado).
- **Install Command**: padrão (`npm install`).
- **Build Command**: padrão (`npm run build` / `next build`).
- **Output**: padrão — o preset Next.js da Vercel cuida disso, sem
  configuração adicional.
- **Node.js Version**: confirme `22.x` em Project Settings → General (o
  `package.json` declara `"engines": { "node": ">=22.12.0" }`).
- **Variáveis de ambiente** (Production — e Preview, se for usar preview
  deployments contra a mesma API):
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
  - `NEXT_PUBLIC_API_URL` = URL pública do Koyeb (passo 3 da ordem de deploy).

## Supabase — Authentication → URL Configuration

Não altere isso agora — só depois que a URL da Vercel existir (passo 11 da
ordem de deploy). Preserve o que já está configurado para desenvolvimento.

- **Site URL**: continua `http://localhost:3000` até a URL definitiva da
  Vercel existir; depois, atualize para `https://<dominio-vercel>`.
- **Redirect URLs** (allow-list, aceita wildcard) — manter a entrada de dev
  e **adicionar** a de produção, nunca substituir:
  ```
  http://localhost:3000/**
  https://<dominio-vercel>/**
  ```
- **Callbacks que o projeto realmente usa** (então é só isso que precisa
  responder sob o domínio configurado):
  - `/auth/callback` — troca o `code` da URL por sessão
    (`frontend/app/auth/callback/route.ts`); usado após confirmação de
    cadastro.
  - `/redefinir-senha` — destino de `resetPasswordForEmail` (recuperação de
    senha); a sessão de recuperação é detectada pelo próprio cliente
    Supabase JS a partir da URL, sem passar por `/auth/callback`.
  - Não há magic link nem OAuth social configurado — só os dois acima.

Nenhum fluxo (cadastro, confirmação, login, logout, recuperação,
redefinição, reenvio de confirmação) depende de `http://localhost:3000`
fixo: todos os redirects usam `window.location.origin` (cliente) ou
`origin` da própria requisição (`route.ts`), então funcionam em dev e em
produção sem mudança de código.

## SMTP / e-mail do Supabase Auth

O projeto **não tem nenhum código próprio de envio de e-mail** — cadastro,
confirmação, recuperação e reenvio de confirmação dependem 100% do serviço
de e-mail do próprio Supabase Auth.

**Limitação crítica a resolver antes de convidar o pai/amiga:** o serviço de
e-mail **padrão** (sem SMTP customizado) do Supabase:
- envia no máximo ~2 e-mails/hora para todo o projeto;
- e, mais importante, **só entrega para endereços que são membros da
  organização Supabase do projeto** — qualquer outro destinatário recebe o
  erro `email_address_not_authorized` e o e-mail nunca chega.
  ([Supabase — Going into prod](https://supabase.com/docs/guides/deployment/going-into-prod),
  [pingram.io — Supabase Auth Emails Not Arriving](https://www.pingram.io/blog/supabase-auth-emails-not-arriving-troubleshooting-guide))

Na prática: **enquanto o SMTP customizado não for configurado, o cadastro do
pai/amiga provavelmente não vai receber o e-mail de confirmação** — não é
um bug deste projeto, é a restrição deliberada do remetente padrão do
Supabase para ambientes de desenvolvimento.

Fluxos que dependem de e-mail: cadastro (confirmação), recuperação de senha,
reenvio de confirmação. Login/logout/refresh de sessão não dependem de
e-mail.

**O que precisa ser configurado (não feito aqui, só documentado — a
instrução foi não configurar provedor externo):**
Supabase → Authentication → Emails → SMTP Settings → habilitar "Custom
SMTP" com um provedor real (SendGrid, AWS SES, Resend, Postmark etc.),
configurar remetente com domínio verificado (SPF/DKIM, para não cair em
spam) e, se necessário, revisar os limites em Authentication → Rate Limits
(o próprio Supabase sobe o limite padrão para 30 e-mails/hora assim que o
SMTP customizado está ativo).

## PWA

Auditoria completa, identidade "Economia UaU":

- `manifest.json`: `name`/`short_name` = "Economia UaU", `display: standalone`,
  `start_url: /inicio`, `background_color`/`theme_color` definidos, ícones
  192×192 e 512×512. OK.
- `apple-touch-icon.png` + `appleWebApp: { capable: true }` configurados via
  `metadata` do Next.js (`app/layout.tsx`) — instalável no iOS/Safari.
- `theme-color` responde a `prefers-color-scheme` (claro/escuro) via
  `viewport.themeColor` — funciona em Android/Chrome e Windows.
- Service worker (`public/sw.js`): cacheia **somente** extensões estáticas
  (`.js .css .png .jpg .jpeg .svg .woff .woff2 .ico`) do próprio domínio;
  ignora explicitamente requisições não-GET, cross-origin e `/api/*`. Nunca
  cacheia JWT, sessão, respostas autenticadas ou dados financeiros — não há
  "modo offline financeiro", só o necessário para a instalação funcionar.

**Bug encontrado e corrigido nesta auditoria:** o matcher do middleware
(`frontend/proxy.ts`) excluía `manifest.json` e `/icons/*` da proteção de
rota, mas **não** excluía `/sw.js`. Resultado: para qualquer usuário ainda
não autenticado (ou seja, todo primeiro acesso antes do login), a
requisição a `/sw.js` era redirecionada para `/entrar` (HTTP 307 com HTML),
o registro do service worker falhava silenciosamente (erro engolido pelo
`.catch()` em `RegistrarServiceWorker.tsx`) e o PWA só ficava de fato
instalável depois do primeiro login bem-sucedido. Corrigido adicionando
`sw\.js` à lista de exclusões do matcher; validado subindo o build de
produção real e confirmando `GET /sw.js` → `200 application/javascript`
sem sessão, com teste de regressão em `frontend/tests/proxy.test.ts`.

Instalação:
- **Android/Chrome**: menu → "Instalar app" (ou prompt automático depois
  que os critérios de instalabilidade — manifest + service worker + HTTPS —
  forem satisfeitos; com o bug acima corrigido, isso já ocorre mesmo antes
  do login).
- **Windows/Chrome/Edge**: ícone de instalação na barra de endereço.
- **iPhone/Safari**: Compartilhar → "Adicionar à Tela de Início" (iOS não
  expõe `beforeinstallprompt`; é sempre manual, mas `apple-touch-icon` e
  `appleWebApp.capable` já estão corretos para isso funcionar bem).

Não bloqueante: nenhum ícone `purpose: "maskable"` no `manifest.json` — bom
para ícones adaptativos no Android, mas os ícones `any` atuais já funcionam.

## Troubleshooting

- **CORS bloqueado no navegador**: confirme que `FRONTEND_URL` no Koyeb tem
  exatamente o(s) domínio(s) usados pelo navegador, sem `/` final (a função
  `origens_permitidas()` já remove, mas confira o valor configurado) e sem
  `*`.
- **401 em toda rota autenticada**: token expirado/sessão não renovada no
  cliente, ou `SUPABASE_URL` errada no backend (JWKS não resolve). Nunca é
  "usuário não tem permissão de dados" — RLS nunca devolve 401, só filtra
  linhas.
- **E-mail de confirmação/recuperação não chega**: ver seção SMTP acima —
  primeiro suspeito é a restrição de "só membros da organização" do
  remetente padrão do Supabase.
- **`ModuleNotFoundError: No module named 'app'` ao subir o backend**:
  rodando de fora de `backend/`. Sempre `cd backend` antes do `uvicorn`, ou
  use o `Dockerfile` (já faz `WORKDIR /app/backend`).
- **Build do Docker falha em `COPY finance_app`**: o *Work directory* do
  Koyeb está apontando para `backend` em vez da raiz do repositório — ver
  seção Koyeb acima.
- **Porta 8000 falha no Windows local** (`WinError 10013`): use 8001 (já é
  o padrão documentado) e ajuste `NEXT_PUBLIC_API_URL` em
  `frontend/.env.local`.
