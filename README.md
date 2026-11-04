# Economia UaU

Organização financeira pessoal multiusuário. Três partes, uma única fonte de
verdade para as regras financeiras:

```
Next.js (frontend/)  ──HTTP + Bearer JWT──▶  FastAPI (backend/)  ──SQL (role app_runtime, RLS)──▶  PostgreSQL (Supabase)
                                                     │
Streamlit (finance_app/) ───────────────────────────┘  (mesma camada de negócio, import direto)
```

- **finance_app/** — aplicação Streamlit original, **continua funcionando normalmente**.
  Contém `src/`, a camada de negócio (contas, categorias, transações, cartões,
  faturas, recorrências, categorizador, resumo financeiro, analytics, importador,
  simulador...) — a fonte de verdade de toda regra financeira.
- **backend/** — API FastAPI nova. Não duplica nenhuma regra: importa
  `finance_app/src/` diretamente (ver `backend/app/core/financas_path.py`).
- **frontend/** — Next.js (App Router + TypeScript + Tailwind) novo, mobile-first,
  PWA. Fala só com a API FastAPI — nunca acessa o banco diretamente.

## Por que essa migração

O Streamlit é ótimo para construir rápido, mas tem limites estruturais: sessão não
sobrevive a um refresh de página, a UX em celular é limitada, e cada interação
reroda a página inteira (recalculando tudo). A migração para Next.js + FastAPI
resolve isso em paralelo, sem desligar o que já funciona — ver
`PARIDADE_MIGRACAO.md` para o estado exato de cada funcionalidade nas duas
interfaces, e `PERFORMANCE_MIGRACAO.md` para números medidos.

## Autenticação

Supabase Auth nas duas interfaces. No Streamlit, via chamadas HTTP diretas
(`finance_app/src/auth.py`). No Next.js, via `@supabase/ssr` (sessão em cookies,
renovada a cada requisição pelo middleware — é isso que corrige a limitação do
Streamlit). A API FastAPI nunca confia em identidade enviada pelo cliente: todo
`usuario_id` vem exclusivamente da validação do JWT (ver seção abaixo).

## Isolamento de dados (RLS)

Decisão herdada e reforçada da migração anterior: a role `postgres` do Supabase
tem `BYPASSRLS=true`, então RLS sozinho não protegeria nada com ela. A aplicação
(Streamlit **e** FastAPI) usa a role restrita `app_runtime`
(`APP_DATABASE_URL`) — sem `BYPASSRLS`, sem ser dona de nenhuma tabela — e o
contexto do usuário é propagado via `set_config('app.usuario_id', ...)`
(`src/banco_de_dados.py:conexao_usuario()`), nunca por uma cláusula `WHERE`
manual. Toda política de RLS já existente continua valendo — a API é só mais um
cliente dessa mesma camada.

**Validação do token no FastAPI**: JWT local via JWKS oficial do projeto Supabase
(`backend/app/core/security.py`) — confirmado compatível (o projeto usa chaves
ES256). Sem round-trip de rede por requisição para validar o token. Trade-off
documentado no próprio módulo: validação local não detecta revogação de sessão
antes do token expirar naturalmente (~1h por padrão do Supabase).

**Propagação do contexto para `conexao_usuario()`**: deliberadamente explícita, não
via contextvars atravessando `Depends()` do FastAPI (não há garantia de que isso
funcione de forma confiável com dependencies síncronas — ver comentário em
`backend/app/core/contexto_usuario.py`). Validado empiricamente: 18 testes de
segurança dedicados (`backend/tests/test_seguranca_api.py`) provam que um usuário
nunca acessa dado de outro, nem por ID conhecido, nem via FK.

## Rodando tudo localmente

Três processos independentes, cada um com seu próprio ambiente virtual/`node_modules`:

```bash
# Streamlit (porta 8501)
cd finance_app
.venv/Scripts/python.exe -m streamlit run app.py

# FastAPI (porta 8001 neste ambiente — a 8000 apresentou WinError 10013 em
# testes anteriores no Windows; se 8000 estiver livre na sua máquina, pode
# usá-la e ajustar NEXT_PUBLIC_API_URL em frontend/.env.local de acordo)
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001

# Next.js (porta 3000)
cd frontend
npm run dev
```

**Atenção ao iniciar o backend**: o comando oficial precisa ser executado de
dentro de `backend/` (`cd backend` primeiro), nunca a partir da raiz do repo.
Todo o código em `backend/app/` usa imports absolutos no formato `from
app....`, assumindo que `backend/` é a raiz do `sys.path` — é a mesma
convenção usada pelo Dockerfile (`WORKDIR /app/backend` antes do `CMD
uvicorn app.main:app`) e pelo `pytest.ini` (`pythonpath = .`, com rootdir em
`backend/`). Rodar `python -m uvicorn backend.app.main:app` a partir da raiz
falha com `ModuleNotFoundError: No module named 'app'`, porque a raiz do
repo (e não `backend/`) é adicionada ao `sys.path` nesse caso, e os imports
absolutos do código não enxergam `app` como pacote de topo.

Cada diretório tem seu próprio `.env.example` — copie para `.env`/`.env.local` e
preencha. Detalhes de cada um:

- `finance_app/README.md` — Streamlit, migrations (Alembic), RLS, conciliação,
  analytics, testes.
- `backend/.env.example` — `APP_DATABASE_URL`, `SUPABASE_URL`, `FRONTEND_URL`.
- `frontend/.env.example` — `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL`. Nada privado.

## Testes

```bash
cd finance_app && .venv/Scripts/python.exe -m pytest   # 252 testes
cd backend && .venv/Scripts/python.exe -m pytest        # 26 testes
cd frontend && npm test                                  # 26 testes (Vitest)
cd frontend && npm run test:e2e                          # 12 testes (Playwright, desktop+mobile)
```

## Documentação da API

Com o backend rodando, `http://localhost:8001/docs` (Swagger/OpenAPI, organizado
por tags: Contas, Categorias, Lançamentos, Cartões, Importação, Metas, Simulador,
Dashboard, Compromissos futuros).

## Deploy (preparado, não executado)

- **Frontend**: `npm run build` passa limpo; pronto para Vercel (ou equivalente).
  Variáveis `NEXT_PUBLIC_*` como env vars do projeto.
- **Backend**: sobe com `uvicorn app.main:app`; ver `backend/Dockerfile` (contexto
  de build é a RAIZ do repo, não `backend/`, porque a imagem também precisa de
  `finance_app/`: `docker build -f backend/Dockerfile .`). Pronto para
  Render/Railway/Koyeb/Fly.io (planos gratuitos). CORS restrito a `FRONTEND_URL`
  — nunca `*`.
- **Streamlit**: inalterado, mesma forma de sempre (ex.: Streamlit Community Cloud).

Nenhum segredo no código-fonte em nenhum dos três. Ver `.env.example` de cada
diretório e os `.gitignore` (raiz cobre Python; `frontend/.gitignore` cobre
Node/Next.js).

## O que NÃO foi feito agora (de propósito)

Open Finance automático, app mobile nativo (a API já é desacoplada do Next.js e
pode atender um futuro app React Native/Expo sem mudanças), IA/LLM, score
financeiro arbitrário, Redis, microserviços, filas distribuídas.
