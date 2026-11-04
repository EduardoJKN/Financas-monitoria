# Performance — medições reais (não estimadas)

Todas as medições abaixo foram feitas localmente, neste ambiente de desenvolvimento,
contra o banco Supabase real do projeto, usando os dados reais já existentes (após
o usuário reivindicar os dados legados). Nenhum número foi inventado.

## Descoberta principal: latência de rede por round-trip, não lentidão de query

Medição isolada (`SELECT 1` dentro de `conexao_usuario()`, 5 chamadas sequenciais):

```
chamada 1: 3614.9 ms   (inclui handshake TCP/TLS inicial)
chamada 2:  919.0 ms
chamada 3:  920.2 ms
chamada 4:  920.1 ms
chamada 5:  919.5 ms
```

Isso prova que **cada round-trip de rede a este Postgres (pooler Supabase,
aws-1-us-east-2) custa ~920ms neste ambiente** — mesmo reaproveitando uma conexão
já estabelecida do pool. `EXPLAIN ANALYZE` nas queries reais do dashboard (resumo
por categoria, por mês) mostrou `Execution Time: 0.2ms` — ou seja, **a query em si
é instantânea; o custo é inteiramente de transporte/rede**, não de índice ausente
nem de SQL ineficiente. Por isso nenhum índice foi criado "no escuro" (ver seção
Índices abaixo).

Isto é consistente com o que o relatório da rodada anterior já havia notado
("~4s/teste... latência de rede, não CPU") — agora medido e explicado com precisão.

## Dashboard: round-trips antes/depois

`/api/v1/dashboard/resumo` chama internamente `resumo_financeiro`/
`analise_financeira` mais de dez vezes (cada função de negócio abre sua própria
`conexao_usuario()`). Medido com os dados reais do usuário:

| Versão | Tempo de cálculo (servidor) | Round-trips estimados |
|---|---|---|
| Antes (cada chamada abre conexão própria) | **38.814 s** | ~42 |
| Depois (`transacao_compartilhada()`, Parte 6) | **10.531 s** | ~11 |
| Redução | **−73%** | −74% |

A otimização (`src/banco_de_dados.py:transacao_compartilhada()`) é aditiva e opcional:
faz chamadas aninhadas de `conexao_usuario()` reaproveitarem UMA conexão/transação
em vez de abrir uma nova a cada chamada. Fora desse bloco (todo o Streamlit, e
qualquer código que não o use explicitamente), nada muda — validado pelos 250
testes do finance_app passando sem alteração, incluindo 5 testes novos dedicados
a essa função (`tests/test_transacao_compartilhada.py`).

As ~11 chamadas restantes são consultas SQL genuinamente distintas (ex.:
`projetar_gasto_mes` soma o mês atual + mês passado + 3 meses de histórico = 5
consultas; `gerar_insights` recalcula taxa de economia e comparação por categoria
de novo). Reduzir isso further exigiria reestruturar as funções de
`analise_financeira.py` para aceitar dados pré-buscados como parâmetro, em vez de
cada uma buscar por conta própria — mudança mais invasiva no código já testado do
Streamlit, não feita agora por risco/tempo. Documentado aqui como próximo passo.

## Streamlit vs. dashboard novo — comparação justa

Medi também o tempo de cálculo server-side da página **atual** `1_Visao_Geral.py`
do Streamlit (sem a otimização, porque o Streamlit nunca usa
`transacao_compartilhada()` — não precisa, não foi tocado):

```
Streamlit (1_Visao_Geral.py atual): 10.369 s
FastAPI /dashboard/resumo (otimizado): 10.531 s
```

**Praticamente empatados** — mas o dashboard novo calcula estritamente mais coisa
(taxa de economia, projeção do mês, insights, ranking com percentual) no mesmo
tempo que o Streamlit leva para calcular um subconjunto menor. E essa é só a
comparação de um único carregamento: o Streamlit **recalcula tudo isso a cada
interação** (qualquer widget muda = rerun completo do script); o Next.js com
TanStack Query (staleTime 15s) **não recalcula nada em navegações repetidas** até
uma mutação real invalidar o cache. Na prática, da segunda visita em diante dentro
da janela de cache, o dashboard novo responde instantaneamente (0ms de rede) contra
os ~10s que o Streamlit pagaria de novo.

**Nota honesta sobre os números absolutos:** os ~920ms por round-trip medidos aqui
são específicos deste ambiente de desenvolvimento (rota de rede até o pooler
Supabase em us-east-2). Em um deploy real com backend e Supabase na mesma região
(ou próximos), esse número tende a cair para poucos milissegundos, tornando TODO o
dashboard — otimizado ou não — praticamente instantâneo. A comparação relativa
(Streamlit × API) continua válida independente da região; os valores absolutos, não.

## Índices

Avaliado conforme pedido ("não crie dezenas de índices no escuro"): com o volume
atual de dados (33 transações), o planner do Postgres corretamente escolhe Seq Scan
em vez de usar qualquer índice — confirmado via `EXPLAIN ANALYZE`. **Nenhuma
migration de índice foi criada** porque não há evidência de necessidade. Candidatos
documentados para quando o volume crescer (não criados agora):

- `(usuario_id, data_transacao)` em `transacoes`
- `(usuario_id, tipo, data_transacao)` em `transacoes`
- `(usuario_id, categoria_id, data_transacao)` em `transacoes`

Como toda tabela já tem RLS por `usuario_id`, esses três cobririam os padrões de
acesso mais comuns (listagem por período, resumo por tipo, resumo por categoria)
quando a tabela crescer o suficiente para o planner preferir index scan.

## Cache em processo

`app/core/cache.py`: TTL de 15s por usuário (chave sempre `usuario_id:nome`),
invalidado explicitamente após toda mutação relevante (lançamento, categoria,
regra aplicada, cartão, importação, pagamento de fatura, conciliação). Sem Redis,
como pedido — não há evidência de que seja necessário nesta fase.

## Novo endpoint: `/dashboard/gastos-fora-padrao`

Adicionado nesta rodada (Parte 20 — "Gastos fora do padrão", antes só existia a
função `analise_financeira.gastos_fora_padrao_do_mes`, sem API nem UI).
Deliberadamente **fora** do `/resumo`: para cada categoria de despesa com
lançamento no mês, faz 1 consulta adicional buscando o histórico de 6 meses
dessa categoria (mesmo padrão de round-trip das demais funções de
`analise_financeira`) — para um usuário com, digamos, 5 categorias de despesa
no mês, isso é ~5-7 consultas adicionais, dentro de `transacao_compartilhada()`
(reaproveita uma conexão) e cacheado por usuário (mesmo TTL de 15s dos outros
endpoints de dashboard).

**Nota de metodologia**: não medi o tempo end-to-end deste endpoint específico
contra o Postgres real nesta rodada — a medição anterior (seção acima) exigiu
um token real do Supabase Auth, e esta sessão não teve acesso de navegador
funcional para autenticar (ver pendências no relatório final). A estimativa
analítica acima é consistente com o padrão já medido (~920ms/round-trip neste
ambiente de dev); em produção (backend/Postgres na mesma região), o custo real
tende a ser bem menor. Os 2 testes automatizados (`test_analise_financeira.py`
+ `test_funcional_api.py`) confirmam a corretude da lógica, não a latência.

## Resultado dos builds/testes de performance

- `backend`: 25/25 testes passando, incluindo os novos de segurança.
- `finance_app`: 250/250 testes passando (245 + 5 novos de
  `transacao_compartilhada`), incluindo a suíte completa de isolamento
  multiusuário — a otimização não relaxa RLS em nenhuma hipótese (testado
  explicitamente: `test_isolamento_rls_continua_valendo_dentro_do_bloco_compartilhado`).

## Atualização — Rodada 4 (retomada pós-queda de energia nº 3)

Nenhuma query nova, nenhum endpoint de dashboard alterado e nenhuma otimização
de `transacao_compartilhada()` foi revisitada nesta rodada — os números acima
continuam válidos e não foram remedidos (não há evidência de que tenham mudado:
nenhum arquivo de `finance_app/src/analise_financeira.py`,
`banco_de_dados.py` ou `backend/app/api/v1/dashboard.py` foi tocado). As duas
mudanças desta rodada (despesa no cartão em Lançamentos; mapeamento de coluna
"Tipo" na importação) são puramente de formulário/UI no Next.js — reaproveitam
o mesmo endpoint `PATCH /transacoes/{id}` e `POST /importacoes/csv/previsualizar`
que já existiam e já estavam cobertos pela análise de round-trips acima.

Revalidação completa (sem código novo em `finance_app`/`backend` fora de
Lançamentos/Importação do frontend):
- `backend`: 26/26 testes passando (78s).
- `finance_app`: 252/252 testes passando (18min04s — consistente com a
  latência de rede já documentada, não regressão).
