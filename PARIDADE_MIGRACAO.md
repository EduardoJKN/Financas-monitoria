# Paridade funcional — Streamlit × API/Next.js

Legenda: ✅ completa · 🟡 parcial · ❌ ausente (API existe, UI não)

| Área | Backend (FastAPI) | Frontend (Next.js) | Observação |
|---|---|---|---|
| Auth (login/cadastro/recuperação/reenvio) | ✅ | ✅ | Next.js corrige a limitação do Streamlit: sessão sobrevive a refresh (middleware renova via cookies). **Bug de segurança/correção real encontrado e corrigido nesta rodada**: a validação local do JWT (`backend/app/core/security.py`) não tinha tolerância (`leeway`) a diferença de relógio — o relógio deste servidor está ~23s atrás do relógio do Supabase (medido via header `Date`), fazendo todo token recém-emitido ser rejeitado como `ImmatureSignatureError` por alguns segundos após cada login real. Corrigido com `leeway=60` em `jwt.decode(...)`; confirmado com usuário real que o login agora é estável (antes, todo primeiro carregamento de página após login caía de volta para `/entrar`). 18/18 testes de segurança revalidados. |
| Proteção de rota | ✅ (JWT obrigatório) | ✅ (middleware redireciona para /entrar) | |
| Dashboard / Visão Geral | ✅ (`/dashboard/resumo`, `/categorias`, `/tendencias`, `/insights`) | ✅ | Resumo, Categorias (ranking) e Insights completos. **Tendências** agora tem UI real: seletor de categoria/tipo, gráfico de evolução mensal (Recharts), comparação com mês anterior/média de 3 meses e badge de padrão (crescimento/queda) — tudo vindo de `/dashboard/tendencias`, nada recalculado em TS. |
| Contas | ✅ CRUD + conciliar | ✅ | Cards, conciliação, ativar/desativar, e agora **editar** (nome/tipo/instituição) via modal. |
| Categorias | ✅ CRUD | ✅ | Criar/listar/excluir/**editar** (nome/tipo) e ativar/desativar prontos. **Hierarquia (categoria pai/subcategoria) agora com UI**: árvore visual, criação de subcategoria direto da categoria-pai, seletor de categoria pai no modal de edição. Testado de ponta a ponta (conta real criada, categoria pai + subcategoria, ambas aparecem corretamente na árvore e nos seletores de Lançamentos/Regras). |
| Regras de categorização | ✅ CRUD + preview + aplicar em lote | ✅ | Nova página `/regras`: criar regra, excluir, e "Aplicar" com pré-visualização dos lançamentos sem categoria compatíveis (seleção manual antes de confirmar). Rótulo de categoria já mostra caminho pai > filho quando aplicável. |
| Lançamentos (receita/despesa) | ✅ | ✅ | Criar, listar com filtro/busca, excluir e **editar**, incluindo agora **despesa paga no cartão de crédito** (rádio "Forma de pagamento: Conta / Cartão de crédito" no modal, como no Streamlit) — antes só era possível criar/editar despesa vinculada a conta. "Pagamento de fatura" **não é** um lançamento editável aqui por desenho: vive em `pagamentos_fatura`, tabela separada (sem `tipo` em `transacoes`); seu histórico tem tela própria em Cartões → "Faturas anteriores". O filtro por tipo "Pagamento de fatura" que existia nesta tela foi removido por ser um bug real (sempre retornava erro 422, pois `transacoes.tipo` nunca assume esse valor). |
| Transferências | ✅ | ✅ | Direção correta (origem/destino conforme receita/despesa) via `resolver_contas_transferencia`. |
| Parcelamento | ✅ preview + criar | ✅ | **UI no próprio modal de lançamento**: checkbox "Dividir em parcelas", número de parcelas, prévia do valor por parcela. Testado de ponta a ponta com usuário real: lançamento de R$300 dividido em 3 parcelas de R$100,00 em meses consecutivos, divisão exata confirmada. |
| Recorrências | ✅ CRUD + gerar pendentes + projeção futura | ✅ | Nova página `/recorrencias`: criar/excluir recorrência (receita/despesa, periodicidade mensal/semanal/anual), botão "Gerar pendentes" que chama `/recorrencias/gerar-pendentes` e mostra quantos lançamentos foram criados. |
| Cartões | ✅ CRUD | ✅ | Card visual com barra de limite, fatura atual, pagar fatura, editar. **Histórico de faturas anteriores agora com UI** (botão "Faturas anteriores" no card → modal listando todas as faturas do cartão com mês de referência, vencimento, status e total, reaproveitando `GET /faturas?cartao_id=`, endpoint que já existia sem UI). |
| Faturas / pagamento | ✅ listar/detalhar/pagar/parcial | ✅ | Pagar fatura funciona. Histórico de faturas anteriores com UI própria (ver linha Cartões acima). |
| Importação CSV | ✅ (com revalidação server-side) | ✅ | Fluxo em 5 etapas (Arquivo → Configuração/mapeamento de colunas → Pré-visualização → Revisão por linha → Confirmação). Mapeamento manual de colunas (data/valor/descrição); reclassificação por linha (transferência com escolha da outra conta, pagamento de fatura com escolha do cartão) na UI. **Mapeamento de coluna "Tipo" customizada agora com UI** (fechado nesta rodada): seletor opcional "Coluna de Tipo" na etapa de Configuração e, quando selecionada, um seletor Receita/Despesa/Não importar por valor distinto encontrado na amostra do arquivo (heurística de valor padrão por substring — "credit"/"receit"→Receita, "debit"/"despes"→Despesa — igual ao Streamlit), enviado como `col_tipo`/`mapeamento_tipo` ao mesmo endpoint que já suportava isso. Valores fora da amostra de 10 linhas caem em "Precisam de revisão" e podem ser definidos manualmente por linha, como sempre. |
| Importação OFX | ✅ (com saldo do banco) | ✅ | Mesmo fluxo (sem etapa de mapeamento, que não se aplica a OFX); comparação de saldo do banco vs. saldo calculado pelo app exibida como banner antes da revisão. |
| Conciliação de saldo | ✅ | ✅ | Pré-visualização + confirmação, igual ao Streamlit. |
| Metas | ✅ CRUD + progresso | ✅ | Criar, listar com barra de progresso, **editar** (nome/valores/datas) e excluir. |
| Simulador | ✅ 3 endpoints puros | ✅ | Projeção com gráfico (Recharts). |
| Analytics (insights, tendências, anomalias) | ✅ | ✅ | Insights no dashboard; tendências por categoria com tela própria. **Gastos fora do padrão** (Parte 20, IQR comparado a 6 meses de histórico) agora tem endpoint dedicado (`/dashboard/gastos-fora-padrao`) e seção própria na aba Insights da Visão Geral — antes só existia a função em `analise_financeira.py`, sem API nem UI. |
| Compromissos futuros (Parte 16) | ✅ (`/compromissos/previstos`, novo) | ✅ | Nova página `/compromissos`: cards por mês (parcelas já lançadas, recorrências ativas, faturas conhecidas, total), com aviso explícito de que não é previsão garantida. |
| PWA | — | ✅ | Manifest, ícones, service worker (só assets estáticos), instalável. |

## Resumo honesto

**Não declaro a migração funcionalmente completa.** O que está ✅ nas duas colunas é
real e testado (automatizado + build limpo). O que está 🟡/❌ no frontend em geral
já tem o endpoint correspondente pronto e testado no backend — o trabalho que falta
é majoritariamente de **tela**, não de regra de negócio, exatamente porque a regra
de negócio nunca foi duplicada (está em `finance_app/src/`, reaproveitada por ambos).

Atualizado na 4ª retomada pós-queda de energia: as duas últimas lacunas de UI conscientes
documentadas aqui (edição de despesa no cartão de crédito; mapeamento de coluna "Tipo"
customizada na importação CSV) foram fechadas nesta rodada e testadas com usuário real
no navegador — não só lidas no código. Não há mais lacunas de paridade conhecidas e
conscientes nesta lista.

**Achado mais importante desta rodada não estava na lista de pendências**: ao testar as
duas features acima com login real, o login falhava de forma intermitente logo após
autenticar (voltava para `/entrar`). Investigado até a causa raiz real (não descartado
como "flutuação de rede"): `ImmatureSignatureError` por falta de tolerância a clock skew
na validação do JWT — ver linha "Auth" acima. Esse bug afetava **todo** login real, não
só as duas features testadas; só não tinha sido percebido em rodadas anteriores porque
nenhuma delas chegou a medir o tempo entre emissão do token e a primeira chamada à API
com precisão de segundos.

O Streamlit **continua 100% funcional e com paridade total** com ele mesmo — nada
foi removido ou alterado em comportamento visível para quem usa só o Streamlit,
exceto a refatoração interna da página de Importação (mesmo resultado, código
compartilhado com a API).
