# Economia UaU — App Finanças

Aplicativo multiusuário de organização financeira, construído com Streamlit
e PostgreSQL (Supabase). Cada usuário autenticado só acessa seus próprios
dados — contas, cartões de crédito, transações (incluindo parcelamentos e
lançamentos recorrentes), categorização automática, importação de extratos
(CSV e OFX), conciliação de saldo, metas financeiras, simulador de cenários
e um painel de analytics financeiro — tudo com valores em formato
brasileiro (`R$ 1.234,56`) e interface em português.

## Funcionalidades principais

- **Autenticação** — login, cadastro, recuperação de senha e logout via
  Supabase Auth. Nenhuma página financeira é acessível sem sessão válida.
- **Contas e Categorias** — cadastro com hierarquia de categorias (pai/filha).
- **Lançamentos** — receitas, despesas e transferências; suporte a
  **parcelamento** (com divisão exata em centavos) e **lançamentos
  recorrentes** (mensal/semanal/anual, geração idempotente de pendências).
  Linhas coloridas por tipo (verde/vermelho/azul/roxo).
- **Cartões de crédito** — modelados separadamente de contas bancárias, com
  fatura calculada a partir do dia de fechamento/vencimento, pagamento
  integral ou parcial, e limite utilizado/disponível.
- **Categorização automática** — regras configuráveis (contém / começa com
  / igual), por prioridade, com aplicação retroativa em lançamentos já
  existentes.
- **Importação de extratos** — CSV (com detecção de delimitador/codificação
  e mapeamento de colunas) e OFX, com detecção de duplicidade, comparação de
  saldo com o banco (quando o OFX traz LEDGERBAL) e detecção de "possível
  transferência"/"possível pagamento de fatura" (nunca classificado
  automaticamente — a decisão final é sempre do usuário).
- **Conciliação de saldo** — cada conta pode ter uma data de referência
  (`data_saldo_inicial`); movimentações até essa data não são somadas de
  novo no cálculo do saldo atual. Ação explícita "Conciliar conta" mostra
  saldo calculado, saldo informado e diferença antes de aplicar — nunca cria
  lançamentos falsos para forçar o saldo a bater.
- **Visão Geral** — em abas (Resumo, Categorias, Tendências, Insights):
  saldos, taxa de economia, projeção simples do mês, ranking de receitas e
  despesas por categoria, comparação histórica, tendências de 3+ meses
  consecutivos, insights determinísticos e detecção de gastos fora do padrão
  (estatística simples, sem IA).
- **Metas financeiras** e **Simulador** (tempo para atingir uma meta,
  aporte mensal necessário, projeção de saldo).

## Stack

- [Streamlit](https://streamlit.io/) — interface
- [PostgreSQL](https://www.postgresql.org/) via [Supabase](https://supabase.com/) — banco de dados + autenticação
- [SQLAlchemy](https://www.sqlalchemy.org/) — acesso a dados (SQL explícito, sem ORM declarativo)
- [Alembic](https://alembic.sqlalchemy.org/) — migrations
- [Plotly](https://plotly.com/python/) — gráficos
- [pandas](https://pandas.pydata.org/) — leitura de CSV
- [ofxparse](https://github.com/jseutter/ofxparse) — leitura de OFX
- [requests](https://requests.readthedocs.io/) — chamadas à API do Supabase Auth
- [pytest](https://docs.pytest.org/) — testes automatizados

## Arquitetura multiusuário

### Autenticação

Login, cadastro e recuperação de senha usam o **Supabase Auth** (GoTrue) via
chamadas HTTP diretas (`src/auth.py`), usando a *publishable key* do
projeto. A aplicação nunca armazena nem valida senha — toda credencial vai
direto para o Supabase. A sessão (access_token + dados do usuário) fica em
`st.session_state`; `definir_usuario_atual()` propaga o id do usuário
autenticado para a camada de dados a cada execução de página.

### Isolamento de dados: por que RLS "ligar e esquecer" não bastava

O projeto conecta ao Postgres do Supabase via SQLAlchemy/psycopg2 (conexão
direta, não passa pelo PostgREST). A conexão administrativa usa a role
`postgres`, que **tem `BYPASSRLS = true` e é owner de todas as tabelas**
(confirmado via `SELECT rolbypassrls FROM pg_roles`). Isso significa que
simplesmente habilitar RLS nas tabelas não protegeria nada: essa role
ignora RLS com ou sem política criada.

A solução adotada (migration `0005_adiciona_multiusuario_e_rls`):

1. Uma role nova, **`app_runtime`**, sem `BYPASSRLS`, sem ser superusuário
   e sem ser owner de nenhuma tabela — só com os GRANTs mínimos
   (SELECT/INSERT/UPDATE/DELETE nas tabelas user-scoped). É essa role —
   nunca `postgres` — que atende usuários autenticados
   (`APP_DATABASE_URL`, lida por `src/banco_de_dados.py:obter_engine_app()`).
2. Cada tabela user-scoped tem `usuario_id uuid` (nullable — ver seção de
   dados legados) com `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL
   SECURITY` e uma política `USING/WITH CHECK (usuario_id = app_usuario_atual())`.
3. O contexto do usuário autenticado é propagado por
   `SELECT set_config('app.usuario_id', '<uuid>', true)` no início de cada
   transação — não por `auth.uid()`/JWT do PostgREST (a aplicação não passa
   por ele). A função SQL `app_usuario_atual()` lê essa GUC e é usada em
   todas as políticas.
4. Para tabelas com colunas de FK para outras tabelas user-scoped (ex.:
   `transacoes.conta_id`), o `WITH CHECK` também exige que o registro
   referenciado pertença ao mesmo usuário — necessário porque checagens de
   integridade referencial no Postgres ignoram RLS por padrão, então sem
   essa checagem extra seria possível criar uma transação apontando para a
   conta de outro usuário usando um ID conhecido (mesmo sem conseguir ler
   os dados dessa conta).
5. `categorias` tem uma política ligeiramente diferente: a checagem de
   `categoria_pai_id` precisou ser movida para uma função
   `SECURITY DEFINER` (`app_categoria_pai_valida`, migration `0007`) porque
   uma subconsulta de uma tabela contra ela mesma dentro da própria política
   de RLS causa "infinite recursion detected in policy" no Postgres — um
   comportamento documentado do Postgres, não um bug da aplicação. A
   função roda com privilégio da role administrativa (que ignora RLS) só
   para esse SELECT interno, evitando a recursão sem abrir brecha nenhuma
   (ela mesma confere que `categoria_pai_id` pertence ao usuário informado).

Em código, toda a camada `src/*.py` acessa o banco através de
`conexao_usuario()` (`src/banco_de_dados.py`) em vez de abrir a conexão
diretamente — essa função garante que a GUC do usuário atual está definida
antes de qualquer consulta, e levanta erro se nenhum usuário estiver
autenticado no contexto. Como a filtragem acontece inteiramente no banco,
**nenhuma função de `src/` precisa adicionar `WHERE usuario_id = ...`
manualmente** — `SELECT * FROM transacoes` já retorna só as linhas do
usuário atual.

### Como isso foi validado (não é "confiança", é teste)

- Testado manualmente contra o banco real: dois UUIDs de usuário distintos,
  um cria uma conta, o outro tenta ler por nome, ler por ID conhecido,
  `UPDATE` por ID conhecido e `DELETE` por ID conhecido — todos retornam
  zero linhas afetadas/visíveis, e uma tentativa de `INSERT` em
  `transacoes` apontando `conta_id` para a conta do outro usuário é
  rejeitada pelo Postgres com `new row violates row-level security policy`.
- `tests/test_isolamento_multiusuario.py` automatiza esse tipo de cenário
  para contas, categorias, transações, regras de categorização, metas,
  recorrências, cartões e faturas/pagamentos.
- `tests/test_analise_financeira.py::test_analytics_isolado_por_usuario`
  confirma que o módulo de analytics nunca mistura dados de dois usuários.
- A suíte de testes inteira passa a rodar através da role `app_runtime`
  (não da role administrativa), então qualquer regressão de isolamento
  quebraria os testes existentes também — não é um caminho de teste
  separado do caminho de produção.

### Dados legados (criados antes do multiusuário)

Como o banco já tinha dados reais, a migration é **aditiva**: `usuario_id`
é `nullable`, nenhuma linha existente foi apagada ou alterada. Uma linha
com `usuario_id IS NULL` nunca é visível pela política de RLS (`NULL = `
qualquer coisa nunca é verdadeiro) — ou seja, dados antigos ficam
automaticamente invisíveis a todos até serem explicitamente reivindicados.

O fluxo de reivindicação (`src/migracao_legado.py`) é guardado por uma
tabela de controle de linha única (`migracao_legado`): a primeira pessoa a
clicar em "Associar dados existentes à minha conta" (banner que só aparece
quando ainda há dados sem dono) tem todos os registros `usuario_id IS NULL`
associados à sua conta, atomicamente; qualquer tentativa posterior (por
outra pessoa) é rejeitada — a linha de controle só permite uma reivindicação
na vida do banco. Essa é a única rotina da aplicação que usa a conexão
administrativa para tocar dados de usuário, e é intencionalmente estreita.

## Conciliação de saldo e OFX

`contas.data_saldo_inicial` (migration `0006`, nullable/aditiva) é a data em
que `saldo_inicial` era o saldo real da conta. O cálculo de saldo
(`src/resumo_financeiro.py`) só soma movimentações **posteriores** a essa
data — movimentações anteriores continuam no histórico, só não duplicam o
efeito. Contas sem essa data mantêm o comportamento antigo (soma tudo) e são
sinalizadas na página Contas como "precisa de conciliação".

Ao importar um OFX, `src/ofx.py:ler_saldo_ofx()` extrai `LEDGERBAL`/
`BALAMT`/`DTASOF` (e `AVAILBAL` quando presente) e a página de Importação
mostra saldo do banco vs. saldo calculado vs. diferença — sem ajustar nada
automaticamente. A ação explícita "Conciliar conta" (página Contas) mostra
essa mesma comparação antes de aplicar, e nunca cria lançamentos falsos
para forçar o saldo a bater.

## Analytics (`src/analise_financeira.py`)

Toda análise financeira é feita por esse módulo, nunca diretamente nas
páginas. Como as funções usam `resumo_financeiro`/`transacoes` por baixo
(que já passam por `conexao_usuario()`), toda análise já é automaticamente
restrita ao usuário autenticado — nenhuma consulta agrega dados de outro
usuário nem calcula médias globais. Nenhum cálculo usa IA/LLM nem define um
"score" arbitrário: tudo é determinístico e explicável a partir dos
números do próprio usuário (ranking de categorias, comparação com média de
3 meses, tendência de 3+ meses consecutivos, taxa de economia, projeção
simples do mês — despesas acumuladas / dias decorridos × dias do mês — e
detecção de gastos fora do padrão via regra do IQR, com amostra mínima).

## Requisitos

- Python 3.11+
- Um projeto [Supabase](https://supabase.com/) (Postgres + Auth)

## Instalação

### 1. Clonar o repositório e criar o ambiente virtual

```bash
git clone <url-do-repositorio>
cd finance_app
python -m venv .venv
```

Ativar o ambiente virtual:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

### 2. Instalar as dependências

```bash
pip install -r requirements.txt
```

Para desenvolvimento (inclui pytest):

```bash
pip install -r requirements-dev.txt
```

### 3. Configurar o `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha (ver `.env.example` para o formato exato):

- `DATABASE_URL` — conexão administrativa (role `postgres`/owner do projeto
  Supabase — a mesma que já existia antes do multiusuário).
- `APP_DATABASE_URL` — conexão de execução, usando a role `app_runtime`
  (criada pela migration `0005`; veja "Passos manuais no Supabase" abaixo
  para a senha).
- `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` — em Project Settings > API
  no painel do Supabase.
- `APP_URL` — opcional; URL pública desta aplicação (ex.:
  `http://localhost:8501` em desenvolvimento), usada como
  `email_redirect_to` ao cadastrar e ao reenviar confirmação de e-mail.
  Sem ela, o Site URL configurado no painel do Supabase é usado como
  fallback.

> O `.env` nunca deve ser commitado — já está no `.gitignore`.

Em produção (ex.: Streamlit Community Cloud), as mesmas variáveis podem ser
definidas em `.streamlit/secrets.toml` (também ignorado pelo git) em vez de
`.env`; `app.py` lê de `st.secrets` automaticamente quando a variável não
está definida localmente.

### 4. Rodar as migrations

Com o banco acessível e `DATABASE_URL` configurada:

```bash
alembic upgrade head
```

Isso cria as tabelas do domínio financeiro e, a partir da migration `0005`,
também cria a role `app_runtime`, as políticas de RLS e a tabela de
controle de migração de dados legados.

Para conferir a revisão atual do banco:

```bash
alembic current
```

### 5. Passos manuais no Supabase (depois do `alembic upgrade head`)

A migration cria a role `app_runtime` **sem senha** de propósito (nunca
gerar/commitar senha em uma migration). Defina a senha manualmente — pelo
SQL Editor do Supabase ou via `psql` com a connection string de
`DATABASE_URL` — e configure `APP_DATABASE_URL` com ela:

```sql
ALTER ROLE app_runtime WITH PASSWORD 'escolha-uma-senha-forte-aqui';
```

Depois monte `APP_DATABASE_URL` com essa senha, usando o mesmo host/porta
de `DATABASE_URL` mas troque o usuário para `app_runtime.<project_ref>`
(o Supabase usa esse formato de usuário — `role.project_ref` — no pooler;
`<project_ref>` é o mesmo trecho que já aparece no usuário de
`DATABASE_URL`).

Outros passos manuais (painel Supabase):

- **Auth > URL Configuration**: configure a Site URL e Redirect URLs para o
  domínio onde o Streamlit vai rodar (necessário para o link de
  recuperação de senha funcionar fora do localhost). Em produção, defina
  também `APP_URL` com essa mesma URL — a aplicação a usa explicitamente
  como `email_redirect_to` ao cadastrar/reenviar confirmação, em vez de
  depender só desta configuração do painel.
- **Auth > Providers > Email**: confirme se "Confirm email" está habilitado
  conforme sua preferência (a aplicação já trata os dois casos — login
  imediato ou exigência de confirmação por e-mail).

### 6. Executar o Streamlit

```bash
streamlit run app.py
```

O app abre em `http://localhost:8501` por padrão. Sem sessão autenticada, a
única tela disponível é Entrar/Criar conta/Recuperar senha.

## Rodando os testes

```bash
pytest
```

Os testes usam o mesmo banco configurado em `APP_DATABASE_URL`/
`DATABASE_URL` — cada teste cria seus próprios dados (sob um UUID de usuário
de teste) e os remove ao final (via fixtures ou blocos `try/finally`), sem
deixar resíduos. **Recomendado rodar contra um banco de desenvolvimento,
não contra dados reais.**

Para rodar só um arquivo específico:

```bash
pytest tests/test_isolamento_multiusuario.py -v
```

## Estrutura do projeto

```
finance_app/
├── app.py                     # autenticação + ponto de entrada do Streamlit
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.example
├── migrations/
│   └── versions/               # uma migration por alteração de schema
├── pages/                      # uma página Streamlit por arquivo
│   ├── 1_Visao_Geral.py        # abas: Resumo / Categorias / Tendências / Insights
│   ├── 2_Lancamentos.py        # inclui parcelamento e recorrências
│   ├── 3_Contas.py             # inclui conciliação de saldo
│   ├── 4_Categorias.py         # inclui regras de categorização
│   ├── 5_Importacao.py         # CSV e OFX, com conciliação e detecção de transferência/fatura
│   ├── 6_Metas.py
│   ├── 7_Simulador.py
│   └── 8_Cartoes.py
├── src/                         # toda a lógica de negócio e acesso a dados
│   ├── banco_de_dados.py        # engines, contexto do usuário autenticado, conexao_usuario()
│   ├── auth.py                  # Supabase Auth (signup/login/logout/recover)
│   ├── migracao_legado.py       # reivindicação de dados legados
│   ├── categorias_padrao.py     # categorias sugeridas para usuário novo
│   ├── analise_financeira.py    # analytics (Partes 13-21)
│   ├── contas.py / categorias.py / transacoes.py
│   ├── categorizador.py         # regras de categorização automática
│   ├── recorrencias.py
│   ├── cartoes.py / faturas.py
│   ├── importador.py            # pipeline compartilhado CSV/OFX (parsing, duplicidade, detecção)
│   ├── ofx.py / graficos.py / formatacao.py / datas.py
│   ├── resumo_financeiro.py     # saldos, conciliação, resumos por período/categoria/mês
│   ├── metas.py / simulador.py
└── tests/                       # suíte pytest (um arquivo por módulo de src/)
```

As páginas (`pages/`) não executam SQL diretamente — toda a lógica fica em
`src/`, o que também é o que torna os testes possíveis sem precisar do
Streamlit.

## Preparação para deploy

1. Provisionar um projeto Supabase e rodar `alembic upgrade head` com
   `DATABASE_URL` apontando para ele.
2. Seguir os passos manuais da seção acima (senha de `app_runtime`,
   Redirect URLs do Auth).
3. Configurar `DATABASE_URL`, `APP_DATABASE_URL`, `SUPABASE_URL`,
   `SUPABASE_PUBLISHABLE_KEY` e `APP_URL` (com a URL pública de produção)
   como variáveis de ambiente/secrets do serviço de hospedagem escolhido.
4. Publicar com `streamlit run app.py` (ou o equivalente do serviço).

Nenhum segredo fica no código-fonte; `.env`, `.env.*` (exceto
`.env.example`) e `.streamlit/secrets.toml` estão no `.gitignore`. A
aplicação nunca expõe SQL, traceback, connection string, credenciais ou JWT
completo no frontend — erros de banco são sempre encapsulados em
`ErroBancoDeDados` com mensagem genérica antes de chegar à interface.

## Ainda não implementado (planejado para fases futuras)

Open Finance/API bancária automática, integração direta com bancos,
investimentos complexos, cotação de ações/cripto, IA/LLM e recomendações
automáticas, score financeiro arbitrário, notificações, compartilhamento
familiar/contas conjuntas.
