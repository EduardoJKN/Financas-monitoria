# Relatório — Evolução arquitetural: Next.js + FastAPI em paralelo ao Streamlit

## 1. Diagnóstico inicial

- `git status` limpo, HEAD em `b8f8d58` (feat: multiusuário/conciliação/analytics) ao iniciar.
- `finance_app/` intacto: Streamlit + `src/` (camada de negócio) + Alembic + RLS
  multiusuário já validados em rodadas anteriores (250 testes, incluindo 7 de
  isolamento multiusuário dedicados).
- Node v24 / npm 11 / Python 3.11 disponíveis.
- Confirmado via query real: JWKS do projeto Supabase responde 200 com chave
  ES256 (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`) — habilita validação
  JWT **local** no backend, a opção preferida do escopo.

## 2. Estrutura criada

```
App Finanças/
├── finance_app/        # Streamlit — inalterado em comportamento, 3 arquivos
│                        #   modificados (ver seção 28) + 2 módulos novos
├── backend/             # FastAPI — novo, venv próprio
│   ├── app/{core,api/v1,schemas}/
│   └── tests/
├── frontend/             # Next.js — novo, App Router + TS + Tailwind
│   ├── app/, components/, features/, hooks/, lib/
│   └── tests/, e2e/
├── PARIDADE_MIGRACAO.md
├── PERFORMANCE_MIGRACAO.md
└── README.md             # novo, raiz do repo
```

## 3. Estratégia de reaproveitamento do Python

**Decisão: não mover nem copiar `finance_app/src/`.** `backend/app/core/financas_path.py`
adiciona `finance_app/` ao `sys.path` (mesma técnica que `migrations/env.py` já
usava para o Alembic — não é uma novidade neste projeto). A partir daí,
`from src import contas` no backend resolve para o **mesmo arquivo** que o
Streamlit usa. Reorganizar em um pacote instalável foi avaliado e descartado:
mais arriscado que necessário, sem benefício real neste estágio.

Única exceção, também aditiva: a lógica de "confirmar uma linha classificada da
importação" (transferência com direção correta, pagamento de fatura sem dupla
contagem) vivia inline na página Streamlit. Extraí para
`src/importacao_execucao.py` (módulo novo, testado) e atualizei a página
Streamlit para chamá-lo — eliminando a duplicação que existiria se o backend
reimplementasse essa mesma decisão. Suíte do Streamlit revalidada (250/250)
depois da troca.

## 4. Backend FastAPI

`GET /health` → `{"status": "ok"}`. Tudo sob `/api/v1`. JSON puro, nenhum HTML.
38 rotas registradas (ver seção 8). `backend/requirements.txt` reaproveita
`finance_app/requirements.txt` via `-r ../finance_app/requirements.txt` em vez
de duplicar versões.

## 5. Autenticação da API

Frontend autentica via Supabase Auth (cliente `@supabase/ssr`) e envia
`Authorization: Bearer <access_token>` em toda chamada (`lib/api/client.ts`).
O backend **nunca** aceita `X-User-ID`, `usuario_id` em query/body, ou qualquer
outro dado de identidade vindo do cliente — só o claim `sub` de um token com
assinatura validada.

## 6. Validação JWT

**Local, via JWKS** (preferência nº 1 do escopo, confirmada compatível).
`backend/app/core/security.py`: `PyJWKClient` busca e cacheia as chaves
públicas do projeto (1h), `jwt.decode(..., algorithms=["ES256"], audience="authenticated")`
valida assinatura + `exp` + `aud`. Zero round-trip de rede por requisição.

**Trade-off documentado explicitamente no código**: validação local não detecta
revogação de sessão (logout remoto) antes do token expirar naturalmente
(~1h por padrão do Supabase) — limitação inerente a qualquer validação JWT
puramente local, não uma lacuna desta implementação. Mitigação futura, se
necessário: reduzir o lifetime do token no painel Supabase, ou reintroduzir
checagem remota periódica (o Streamlit já faz isso via
`src/auth.py:validar_ou_renovar_sessao`, não replicado aqui para manter simples).

## 7. RLS

Role de execução continua `app_runtime` (sem `BYPASSRLS`, sem ownership) — a
mesma do Streamlit. **Descoberta de risco técnico real durante a implementação**:
contextvars não têm propagação garantida entre uma FastAPI `Depends()` síncrona
e o endpoint (FastAPI pode despachar cada uma em invocações de thread-pool
separadas). Em vez de confiar nesse detalhe de implementação para algo
security-critical, o desenho é **explícito**: `usuario_id` chega via parâmetro
normal de função (`Depends(obter_usuario_atual)`, isso não tem ambiguidade), e
um decorator (`app/core/contexto_usuario.py:com_usuario`) chama
`definir_usuario_atual(usuario_id)` **dentro da mesma chamada de função** que
executa o corpo do endpoint — nunca atravessando um limite de thread/contexto
separado. Documentado em detalhe no próprio módulo.

## 8. Como RLS foi validado de verdade

18 testes dedicados (`backend/tests/test_seguranca_api.py`) usando um par de
chaves EC gerado só para teste (JWKS real do Supabase nunca tocado nos testes —
zero usuário real criado/órfão): sem token → 401; token malformado → 401;
assinatura inválida → 401; expirado → 401; audience errada → 401. Usuário B
tentando, via API real + banco real: listar/obter/alterar/excluir conta de A,
obter categoria de A, criar transação usando `conta_id` de A (ataque via FK
conhecido), acessar cartão de A, acessar meta de A, e ver dados de A no
dashboard agregado — **tudo bloqueado**, confirmado por asserção, não por
inspeção de código. Mais 7 testes funcionais (`test_funcional_api.py`): CRUD,
parcelamento com divisão exata em centavos, paginação, simulador, e confirmação
de que erros 422/404 nunca vazam SQL/traceback/stack.

## 9. Endpoints criados (38 rotas, `/api/v1`)

Contas (5 + conciliar + pré-visualizar), Categorias (5), Regras (5 + preview +
aplicar + aplicar-todas), Transações (5 + parcelamento preview/criar),
Recorrências (5 + gerar-pendentes), Cartões (5), Faturas (4), Importação (3:
csv/previsualizar, ofx/previsualizar, confirmar), Metas (5), Simulador (3),
Dashboard (4: resumo/categorias/tendencias/insights), Compromissos (1, novo —
Parte 16). Tags organizadas no OpenAPI (`/docs`).

## 10. Otimizações de banco

`EXPLAIN ANALYZE` nas queries do dashboard: `Execution Time: 0.2ms` com os
dados atuais — **nenhum índice criado**, porque não há evidência de necessidade
(Postgres corretamente prefere Seq Scan nesse volume). Candidatos documentados
em `PERFORMANCE_MIGRACAO.md` para quando o volume crescer, não criados agora
("não no escuro").

O achado real foi outro: **~920ms de latência de rede por round-trip** a este
Postgres neste ambiente (medido isoladamente, 5 chamadas sequenciais). Isso
tornava `/dashboard/resumo` lento não por SQL ruim, mas porque cada função de
negócio chamada internamente abria sua própria conexão. Corrigido com
`src/banco_de_dados.py:transacao_compartilhada()` — otimização aditiva e
opcional (zero efeito fora de quem a usa explicitamente) que reaproveita uma
única conexão para todas as chamadas aninhadas de `conexao_usuario()` dentro do
bloco. Validada com 5 testes novos dedicados, incluindo que o isolamento RLS
continua intacto dentro do bloco compartilhado.

## 11. Dashboard: queries antes/depois

| | Tempo medido (dados reais) | Round-trips |
|---|---|---|
| Antes | 38.814 s | ~42 |
| Depois | 10.531 s | ~11 |

**−73%**. Detalhes completos, incluindo comparação honesta com o Streamlit
atual (10.369s para calcular um subconjunto menor de analytics — praticamente
empatado, mas o novo dashboard faz mais no mesmo tempo, e cacheia no cliente o
que o Streamlit recalcularia a cada interação), em `PERFORMANCE_MIGRACAO.md`.

## 12. Frontend Next.js

App Router, TypeScript estrito, Tailwind v4 (tema claro/escuro via classe,
paleta própria com cores semânticas acessíveis). `@supabase/ssr` para auth,
TanStack Query para cache/mutação, Recharts para gráficos, lucide-react para
ícones. Sem bibliotecas de UI pesadas (nada de MUI/Chakra/Ant) — componentes
próprios e enxutos.

## 13. Design system

14 componentes em `components/ui/`: Button, Input, Select, Card, MetricCard,
Modal, Badge (+BadgeTipo com as 4 cores de lançamento), EmptyState,
LoadingSkeleton, Money, DateDisplay, DataTable (tabela desktop → cards mobile),
PageHeader, ConfirmDialog, mais Tabs (abas desktop → seletor mobile). Todos com
label associado, `aria-*`, foco visível.

## 14. Experiência desktop

Sidebar fixa (9 itens), usuário + toggle de tema + Sair. Conteúdo centralizado,
max-width, tabelas reais para listas longas (lançamentos).

## 15. Experiência mobile

Bottom navigation (4 itens mais usados) + menu "Mais" em drawer para o resto —
nunca uma sidebar espremida. Listas viram cards. Testado em 390px via Playwright
(viewport mobile real, não só CSS). Modais ocupam quase a tela toda em telas
pequenas, centralizados em desktop.

## 16. Dashboard novo

4 abas (Resumo/Categorias/Tendências/Insights — seletor em mobile, abas em
desktop). Resumo e Categorias (ranking Top N + Outros, Recharts) completos e
testados. Insights classificados visualmente (positivo/atenção/info) a partir
do texto já gerado por `analise_financeira.py` — **nenhum analytics recriado em
TypeScript**. Tendências é placeholder (endpoint pronto, UI não construída —
ver `PARIDADE_MIGRACAO.md`).

## 17. PWA

`manifest.json` (nome, ícones 192/512, standalone, theme_color claro/escuro),
ícones gerados (Pillow, temporários como pedido), `sw.js` cacheando **somente**
assets estáticos por extensão — nunca `/api/`, nunca cross-origin, nunca uma
página HTML autenticada. Testável via "instalar app" no Chrome.

## 18. Sessão persistente

Corrige a limitação conhecida do Streamlit: middleware (`lib/supabase/middleware.ts`)
renova a sessão via cookies HTTP-only a cada requisição. Refresh de página não
desloga mais o usuário. Logout limpa o cache do TanStack Query inteiro (nunca
mistura dados entre usuários no mesmo navegador).

## 19. Testes backend

25 testes (`backend/tests/`): 18 de segurança + 7 funcionais. 100% passando.

## 20. Testes frontend

26 testes Vitest + React Testing Library: formatadores (moeda/data/percentual —
achei e corrigi uma divergência real de espaço não-separável entre `Intl` e o
Streamlit, ver seção 22), parser de decimal brasileiro, componentes (Badge,
Button, Money, EmptyState), e tela de login com Supabase mockado (sem usuário
real). 100% passando. `npm run typecheck`/`npm run lint`: limpos (3 avisos
intencionais sobre `window.location.href`, não erros).

## 21. Testes RLS

Cobertos na seção 8 (18 testes dedicados no backend) **mais** 5 testes novos no
finance_app para `transacao_compartilhada()` confirmando que a otimização de
performance não relaxa isolamento — e os 7 testes de isolamento multiusuário
já existentes continuam passando sem alteração.

## 22. Paridade Streamlit × Next.js

Ver `PARIDADE_MIGRACAO.md` — honesto, não infla. Auth, Contas, Cartões, Metas,
Simulador, Lançamentos/Transferências/Conciliação: ✅ nas duas interfaces.
Regras de categorização, Recorrências, Compromissos futuros: ✅ backend, ❌ UI.
Importação: 🟡 (funciona, mas sem mapeamento manual de colunas nem
reclassificação de linha por transferência/fatura na tela — a API já suporta).
Achado colateral relevante: a formatação de moeda do `Intl.NumberFormat`
brasileiro usa espaço não-separável (` `) entre "R$" e o número — diferente
do espaço comum que `formatacao.py` usa no Streamlit. Corrigido montando a
string manualmente no frontend para ficar byte-a-byte igual.

## 23. Performance medida

Ver seções 10/11 e `PERFORMANCE_MIGRACAO.md` — números reais, metodologia
descrita, nada inventado.

## 24. Build do Next

`npm run build` — limpo, 18 rotas (15 páginas + raiz + not-found + callback),
TypeScript sem erros. Aviso informativo do Next 16 sobre "middleware" →
"proxy" (convenção renomeada nesta versão; `middleware.ts` continua funcionando
normalmente, não é erro).

## 25. Resultado FastAPI

`uvicorn app.main:app` sobe sem erro. `GET /health` → `200 {"status":"ok"}`.
25/25 testes passando.

## 26. Resultado Streamlit

`streamlit run app.py --server.headless true` → HTTP 200, sem erro no log.
250/250 testes passando (suíte completa, incluindo os 2 módulos novos
reaproveitados pelo backend).

## 27. Migrations

**Nenhuma migration nova nesta rodada.** Nenhuma mudança de schema foi
necessária — tudo que o backend precisa (RLS, `usuario_id`, `app_runtime`) já
existia da rodada anterior. `alembic current` == `alembic heads` == `0007`,
confirmado no banco real.

## 28. Arquivos alterados (finance_app, tracked)

```
.gitignore                          (+Node/Next.js)
finance_app/pages/5_Importacao.py   (usa importacao_execucao, remove duplicação)
finance_app/src/banco_de_dados.py   (+transacao_compartilhada, aditivo)
finance_app/src/recorrencias.py     (+projetar_proximas_ocorrencias, aditivo)
```

## 29. Arquivos criados

```
README.md, PARIDADE_MIGRACAO.md, PERFORMANCE_MIGRACAO.md   (raiz)
finance_app/src/importacao_execucao.py
finance_app/src/compromissos_futuros.py
finance_app/tests/test_importacao_execucao.py
finance_app/tests/test_compromissos_futuros.py
finance_app/tests/test_transacao_compartilhada.py
backend/                                                     (46 arquivos)
frontend/                                                     (90 arquivos)
```

## 30. git diff --stat

```
.gitignore                        | 10 +++++++
finance_app/pages/5_Importacao.py | 63 ++++++++-------------------------------
finance_app/src/banco_de_dados.py | 52 ++++++++++++++++++++++++++++++++
finance_app/src/recorrencias.py   | 39 ++++++++++++++++++++++++
4 files changed, 113 insertions(+), 51 deletions(-)
```

## 31. git status

4 modificados, 10 entradas novas não rastreadas (3 arquivos .md + backend/ +
frontend/ + 5 arquivos novos em finance_app). Nada staged — nenhum `git add`
executado.

## 32. Pendências

- UI de Importação simplificada (sem mapeamento de colunas / reclassificação
  de linha) — maior lacuna de paridade real, ver seção 22.
- Tendências do dashboard: placeholder.
- Regras de categorização, Recorrências, Compromissos futuros: sem página
  própria (só API).
- Edição (PATCH) de lançamentos/contas/categorias/metas: endpoint existe, UI
  só tem criar/excluir na maioria.
- Validação de revogação de sessão no backend é local-only (trade-off
  documentado na seção 6).
- Node reportou 5 vulnerabilidades "high" via `npm audit` — todas em
  `eslint-config-next` (dependência de lint, build-time, não runtime do app
  publicado); deixadas como estão para não forçar downgrade quebrando o
  eslint config atual.
- Descobri (não causei) que o usuário real reivindicou os dados legados e
  logou no próprio app durante esta sessão — mencionado aqui só porque mudou
  os números de "dados de teste" que eu estava observando; não precisei agir
  sobre isso, é uso legítimo do próprio usuário.

## 33. Passos manuais no Supabase

Nenhum passo novo — a infraestrutura (role `app_runtime`, RLS, JWKS) já estava
pronta da rodada anterior. Para produção, lembrar de adicionar o domínio real
do Next.js em **Auth > URL Configuration > Redirect URLs** quando o deploy
acontecer (não feito agora, só documentado).

## 34. Instruções para rodar tudo localmente

Ver seção "Rodando tudo localmente" do novo `README.md` da raiz — três
comandos, três portas (8501/8000/3000), cada um com seu próprio `.env`.

## 35. Sugestões de deploy gratuito

- **Frontend**: Vercel (plano Hobby) — é o próprio criador do Next.js, zero
  configuração além das env vars `NEXT_PUBLIC_*`.
- **Backend**: Render ou Railway (planos free/starter) — suportam Docker
  (`backend/Dockerfile`, contexto = raiz do repo) ou build Python direto.
  Fly.io e Koyeb são alternativas equivalentes.
- **Streamlit**: Streamlit Community Cloud, como já documentado no
  `finance_app/README.md`.

---

## Mensagens de commit sugeridas (dividir manualmente)

```
1. chore: adiciona .gitignore para node/next e prepara estrutura multi-app
2. refactor: extrai confirmacao de importacao para modulo compartilhado
3. perf: adiciona reaproveitamento opcional de conexao (transacao_compartilhada)
4. feat: adiciona projecao de proximas ocorrencias de recorrencias
5. feat: adiciona backend fastapi com auth jwt local e isolamento rls
6. feat: adiciona frontend nextjs com dashboard responsivo e pwa
7. docs: adiciona readme raiz, paridade e performance da migracao
```

**NÃO EXECUTADO**: `git add`, `git commit`, `git push`. Nenhum comando git além
de inspeção (`status`, `diff`, `log`) foi rodado nesta sessão.
