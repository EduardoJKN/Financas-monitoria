# Relatório — Rodada 2 (correções técnicas + validação + gaps de UX)

Continuação de `RELATORIO_MIGRACAO_NEXTJS.md` (rodada 1). Este documento cobre
só o que mudou **nesta** rodada — não repete o que já estava descrito lá.

## 1. Estado inicial encontrado

`git status` já tinha a estrutura completa de `backend/` e `frontend/` de uma
rodada anterior, bem mais madura do que o pedido sugeria: 12 páginas do painel
já implementadas (Início, Visão Geral com 4 abas, Lançamentos, Contas, Cartões,
Categorias, Regras, Recorrências, Importação em wizard, Metas, Simulador,
Compromissos), 21 componentes de design system em `components/ui/`, PWA
funcional (manifest, service worker restrito a assets estáticos, ícones),
tema claro/escuro/sistema, bottom nav mobile + sidebar desktop, e
`PARIDADE_MIGRACAO.md`/`PERFORMANCE_MIGRACAO.md` já com números reais
medidos. Ajustei o escopo desta rodada de acordo: em vez de redesenhar do
zero, priorizei corrigir os problemas técnicos relatados, validar tudo de
verdade, e fechar lacunas concretas encontradas por auditoria de código.

## 2. Correção do FastAPI

Não havia bug — `ModuleNotFoundError: No module named 'app'` ao rodar
`python -m uvicorn backend.app.main:app` da raiz é esperado: todo
`backend/app/` usa imports absolutos (`from app...`), e isso só resolve com
`backend/` como raiz do `sys.path`. O `README.md` já documentava a forma
correta. **Validei de verdade**: `cd backend && python -m uvicorn app.main:app
--port 8001` sobe limpo, `/health` → 200, `/docs` → 200, `/openapi.json` → 200.

## 3. Comando oficial do backend

```powershell
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001
```

Testei também a porta 8000 (motivo do WinError 10013 relatado): **neste
ambiente, 8000 respondeu normalmente agora** (`/health` → 200). Pode ter sido
transitório (outro processo ocupando a porta no teste anterior) ou uma
reserva de porta do Windows que não está mais ativa. Mantive **8001** como
padrão documentado, por instrução explícita — se quiser padronizar em 8000
depois de confirmar que fica estável, é só trocar `--port` e
`NEXT_PUBLIC_API_URL`.

## 4. Correção do npm install

Também não havia conflito: `package.json` já tinha `@types/node: "^24"`,
compatível com `vitest ^5` (exige `^22 || >=24`). **Validei com instalação
limpa de verdade** (não só `npm install` incremental): mudei `node_modules/` e
`package-lock.json` de lugar, rodei `npm install` do zero → **sem ERESOLVE**,
504 pacotes instalados em ~20 min (ambiente lento neste Windows — não há sinal
de travamento, é I/O real; ver seção 21). Restaurei nada manualmente — o
install novo é que ficou valendo, idêntico em versões ao anterior.

## 5. Versões Node/npm validadas

```
node -v → v24.13.1
npm -v  → 11.8.0
```
Compatíveis com `engines.node: ">=22.12.0"` do `package.json`.

## 6. Design system

Já existia e é sólido: 21 componentes (`Button`, `Input`, `Select`, `Card`,
`MetricCard`, `Modal`, `Badge`/`BadgeTipo`, `EmptyState`, `LoadingSkeleton`,
`Money`, `DateDisplay`, `DataTable`, `PageHeader`, `ConfirmDialog`, `Tabs`,
`ConfirmDialog`...). Tokens semânticos em `globals.css` (`--background`,
`--superficie`, `--borda`, `--primaria`, + 4 pares fundo/texto por tipo de
lançamento) com variantes clara/escura via classe `.dark` e
`prefers-color-scheme`. Não precisei recriar nada — revisei e confirmei que
segue exatamente os princípios pedidos (cor sempre + ícone/texto, nunca só
cor; fundo da linha inteira por tipo de lançamento). Não encontrei
inconsistência que justificasse refatoração.

## 7. Principais decisões de UX desta rodada

- **Não reescrevi páginas que já atendiam ao pedido.** O risco de regressão
  (e o custo de descartar trabalho testado) superava o ganho de "redesenhar
  por redesenhar". Troquei esforço por auditoria dirigida: comparei cada
  seção do pedido do usuário com o código real, e só mexi onde havia uma
  lacuna concreta.
- **Gastos fora do padrão** (pedido explicitamente, Parte 20) existia como
  função Python (`analise_financeira.detectar_lancamentos_fora_padrao`) mas
  sem API nem UI — essa foi a lacuna mais significativa que encontrei e
  fechei (seção 10).
- **Início** tinha saldo/resultado/taxa/próxima fatura + atalhos, mas faltavam
  "resumo dos últimos lançamentos" e "insights mais relevantes", que o pedido
  especificava explicitamente como parte da Home — adicionei os dois.

## 8. Redesign da Home

Adicionei duas seções que faltavam a `app/(painel)/inicio/page.tsx`:
"Últimos lançamentos" (5 mais recentes, reaproveitando `useTransacoes` e a
mesma cor de fundo por tipo usada em Lançamentos — nunca um componente novo
paralelo) e "Para você" (top 2 insights de `resumo.insights_principais`, que já
vêm prontos de `analise_financeira.gerar_insights`). Nada de analytics novo em
TypeScript — só consumo do que a API já calculava.

## 9. Redesign do Dashboard (Visão Geral)

Já tinha Resumo, Categorias (ranking Top N + Outros), Tendências (gráfico +
comparação + badge de padrão) e Insights — tudo funcional. Faltava
"Gastos fora do padrão" (pedido explicitamente). Implementei de ponta a
ponta:
- Nova função `gastos_fora_padrao_do_mes()` em `analise_financeira.py`
  (aplica a regra IQR já existente a todas as categorias com despesa no mês,
  usando 6 meses de histórico como base estatística — não só o próprio mês).
- Novo endpoint `GET /api/v1/dashboard/gastos-fora-padrao` (fora do
  `/resumo`, para não pesar a rota mais usada — mesmo padrão dos endpoints
  complementares já existentes).
- Nova seção na aba Insights da Visão Geral: card por gasto fora do padrão,
  com categoria, descrição, valor, e a faixa normal ("normalmente entre R$X e
  R$Y") — exatamente como o pedido descrevia, nunca como alarme binário.
- 2 testes novos no `finance_app` + 1 no `backend` (todos passando).

## 10-17. Lançamentos, Contas, Cartões, Categorias, Importação, Metas, Simulador

Revisei o código de cada um (não só a lista — abri e li a implementação
inteira): todos já seguem os princípios pedidos — modal para criar lançamento
(nunca navegação), linha/card colorido por tipo, cards visuais para cartão
(limite/usado/disponível com barra), wizard de 5 passos na importação,
metas com barra de progresso, simulador com gráfico. **Não fiz mudanças
nessas páginas nesta rodada** — não encontrei lacuna que justificasse reescrita
dado o tempo disponível, e every linha nova é risco de regressão num código já
testado. Gaps reais que **já estavam** documentados em `PARIDADE_MIGRACAO.md`
antes desta rodada (parcelamento sem UI no modal, hierarquia de categoria pai
sem UI, histórico de faturas antigas sem UI) continuam como estavam — não os
peguei porque não são bugs nem lacunas da sessão atual, são escopo
conscientemente adiado por quem fez a rodada 1.

## 18. Mobile

Bottom nav (4 itens + "Mais") já implementada e testada via Playwright em
390px (12/12 E2E passando, incluindo viewport mobile). Não tive acesso a
inspeção visual ao vivo nesta rodada (ver seção 33) — validei via leitura de
código + E2E, não via screenshot real.

## 19. Dark/light

Já implementado (`ThemeScript` evita flash, `ThemeToggle` persiste
preferência, 3 estados: claro/escuro/sistema). Não mexi.

## 20. PWA

Já funcional (manifest, SW restrito a assets estáticos, nunca `/api/` nem
dados autenticados). **O que mudei**: o ícone era um placeholder de texto
("UaU" branco sobre fundo azul) — substituí por um símbolo vetorial simples
(sparkline ascendente + ponto verde, gerado via Pillow,
`frontend/scripts/gerar_icones.py`, reexecutável) em `icon-192.png`,
`icon-512.png`, `apple-touch-icon.png` e `favicon.ico`.

## 21. Estado da preparação Tauri

Rust/Cargo não estão instalados neste ambiente — não instalei toolchain de
sistema (fora do escopo autorizado automaticamente). Criei `DESKTOP_TAURI.md`
com arquitetura, pré-requisitos, comandos exatos de scaffold (`tauri init`),
configuração mínima esperada, e como gerar o `.exe` quando alguém com Rust
disponível quiser seguir.

## 22. Performance backend

Números da rodada 1 continuam válidos (não re-medi o que não mudou):
`/dashboard/resumo` 38.8s → 10.5s (−73%) com `transacao_compartilhada()`.
**Novo**: documentei o custo estimado do endpoint `/dashboard/gastos-fora-padrao`
(~5-7 round-trips adicionais, só quando a aba Insights é aberta) —
análise, não medição ao vivo, porque não consegui autenticar no navegador
para pegar um token real (ver seção 33).

## 23. Performance frontend

`npm run build`: compilou em 9.4s + 8.9s de typecheck, 21 rotas (19 páginas +
not-found + callback), todas estáticas exceto `/auth/callback` (dinâmica,
correto). Sem erro, sem warning de middleware (confirmado: `proxy.ts` já
usa a convenção nova do Next 16, `Proxy (Middleware)` aparece limpo no build).

## 24. Número de requests do dashboard

Sem mudança no `/resumo` em si (continua ~11 round-trips internos, ver
`PERFORMANCE_MIGRACAO.md`). O novo endpoint é **separado**, carregado só
quando o usuário abre a aba Insights — decisão deliberada para não aumentar
o número de requests da carga inicial do dashboard.

## 25. Testes backend

**26/26 passando** (25 da rodada 1 + 1 novo:
`test_dashboard_gastos_fora_padrao_retorna_lista_vazia_sem_amostra`). Rota
nova também incluída em `ROTAS_PROTEGIDAS` (teste de 401 sem token).

## 26. Testes frontend

**Lint**: limpo (0 erros, 3 warnings intencionais já documentados — ver
seção 34 sobre um bug que eu mesmo causei e corrigi durante o lint).
**Typecheck**: limpo. **Vitest**: 26/26 passando. **Build**: limpo.

## 27. E2E

**12/12 passando** (desktop + mobile/390px): login renderiza, proteção de
rota redireciona para `/entrar` em `/`, `/compromissos`, `/regras`,
`/recorrencias`, viewport mobile funciona. Não cobre fluxo autenticado (login
real) — decisão já tomada na rodada 1 para não criar usuário de teste no
Supabase real, que eu mantive.

## 28. Streamlit

**HTTP 200** em `localhost:8501`. **250/250 testes** passando em
`finance_app` (24min19s — ambiente com round-trip de rede lento ao Postgres,
não travamento; ver seção 21 do `PERFORMANCE_MIGRACAO.md`), incluindo os 2
testes novos de `gastos_fora_padrao_do_mes`.

## 29. Paridade

Atualizei `PARIDADE_MIGRACAO.md`: linha "Analytics" agora reflete que Gastos
fora do padrão tem API + UI (antes: só função Python). Resto do documento
continua válido — não reavaliei linha por linha porque nenhuma outra área
mudou nesta rodada.

## 30. Arquivos criados

```
DESKTOP_TAURI.md
RELATORIO_RODADA2.md (este arquivo)
frontend/scripts/gerar_icones.py
```

## 31. Arquivos alterados

```
finance_app/src/analise_financeira.py        (+gastos_fora_padrao_do_mes, aditivo)
finance_app/tests/test_analise_financeira.py (+2 testes)
backend/app/api/v1/dashboard.py              (+endpoint /gastos-fora-padrao)
backend/tests/test_seguranca_api.py          (+1 rota em ROTAS_PROTEGIDAS)
backend/tests/test_funcional_api.py          (+1 teste)
frontend/app/(painel)/inicio/page.tsx         (+últimos lançamentos, +insights)
frontend/app/(painel)/visao-geral/page.tsx    (+seção Gastos fora do padrão)
frontend/features/dashboard/hooks.ts          (+useGastosForaPadrao)
frontend/lib/api/types.ts                     (+tipo GastoForaPadrao)
frontend/lib/api/client.ts                    (fallback de porta 8000→8001)
frontend/.env.local                           (porta 8000→8001)
frontend/public/icons/*.png, app/favicon.ico  (ícone novo)
README.md                                     (porta/testes atualizados)
PARIDADE_MIGRACAO.md                          (linha Analytics atualizada)
PERFORMANCE_MIGRACAO.md                       (seção do novo endpoint)
```

## 32. git diff --stat (arquivos JÁ rastreados pelo git)

```
.gitignore                                   | 10 ++++
finance_app/pages/5_Importacao.py            | 63 +++++-----------------  (rodada 1, não mexi)
finance_app/src/analise_financeira.py        | 81 +++++++++++++++++++++++++---
finance_app/src/banco_de_dados.py            | 52 ++++++++++++++++++  (rodada 1, não mexi)
finance_app/src/recorrencias.py              | 39 ++++++++++++++  (rodada 1, não mexi)
finance_app/tests/test_analise_financeira.py | 35 ++++++++++++
6 files changed, 221 insertions(+), 59 deletions(-)
```

`backend/` e `frontend/` continuam untracked (como na rodada 1) — meus
arquivos novos/alterados lá não aparecem em `git diff --stat` por isso.

## 33. Pendências

- **Inspeção visual ao vivo não foi possível nesta rodada**: a automação de
  navegador (Claude in Chrome) falhou consistentemente com "Frame with ID 0
  is showing error page" ao navegar para `localhost:3000`/`127.0.0.1:3000`,
  mesmo em aba nova, mesmo depois de confirmar via `curl` que o servidor
  responde 200 normalmente. Tentei 6 vezes, com variações (URL com/sem
  protocolo explícito, aba nova, resize antes/depois). Não consegui
  diagnosticar a causa raiz (pode ser permissão da extensão para localhost,
  pode ser rede isolada entre o Chrome real e este ambiente de shell). Toda
  validação de UI nesta rodada foi por leitura de código + testes
  automatizados (incluindo E2E com viewport real de 390px), não por
  screenshot. Se quiser a inspeção visual real (telas em 360/390/430/768/
  1024/1440px pedida no escopo), preciso que você verifique a permissão da
  extensão Claude in Chrome para `localhost`/`127.0.0.1`, ou rode localmente
  e me passe screenshots.
- Lacunas de paridade já conhecidas da rodada 1 continuam abertas (seção 10-17
  acima): parcelamento sem UI no modal, hierarquia de categoria pai,
  histórico de faturas antigas, edição de lançamento de cartão/fatura.
- Tauri: só documentado, nenhum scaffold criado (Rust não instalado).
- `npm audit`: 5 vulnerabilidades "high", todas em `eslint-config-next`
  (build-time, não runtime) — herdado da rodada 1, não investiguei de novo.
- Não autentiquei no app com usuário real nesta rodada (ver seção 33) — não
  consegui medir o endpoint novo end-to-end nem ver o dashboard populado
  visualmente.

## 34. Nota sobre um bug que causei e corrigi

Durante o teste de instalação limpa (seção 4), movi `node_modules/` para
`node_modules.bak/` em vez de apagar. Esqueci de removê-lo depois, e o
primeiro `npm run lint` tentou escanear essa pasta inteira (sem estar nos
ignores padrão do ESLint, que só conhece `node_modules/`), girando ~19
minutos de CPU real antes de eu perceber pelo log e encerrar o processo.
Apaguei `node_modules.bak/` e `package-lock.json.bak`, rodei o lint de novo —
limpo em segundos. Reportando porque é exatamente o tipo de coisa que, se eu
não tivesse checado o log, teria me feito reportar "lint travado" sem
explicação.

## 35. Sugestões de divisão dos commits

```
1. fix: corrige porta padrao da API no frontend (8000 -> 8001) e remove fallback hardcoded
2. feat: adiciona deteccao de gastos fora do padrao do mes (analise_financeira)
3. feat: expoe endpoint /dashboard/gastos-fora-padrao e testes
4. feat: adiciona secao "gastos fora do padrao" na Visao Geral e "ultimos lancamentos"/"insights" na Home
5. feat: substitui icone placeholder do PWA por simbolo proprio (sparkline)
6. docs: adiciona DESKTOP_TAURI.md e atualiza README/PARIDADE/PERFORMANCE
```

**NÃO EXECUTADO**: `git add`, `git commit`, `git push`, nem qualquer comando
destrutivo. Só `status`, `diff`, `diff --stat`, `log` foram usados para
inspeção.
