# Economia UaU — App Finanças

Aplicativo pessoal de organização financeira, construído com Streamlit e
PostgreSQL. Permite controlar contas, cartões de crédito, transações
(incluindo parcelamentos e lançamentos recorrentes), categorização
automática, importação de extratos (CSV e OFX), metas financeiras e um
simulador de cenários — tudo com valores em formato brasileiro (`R$
1.234,56`) e interface em português.

## Funcionalidades principais

- **Contas e Categorias** — cadastro com hierarquia de categorias (pai/filha).
- **Lançamentos** — receitas, despesas e transferências; suporte a
  **parcelamento** (com divisão exata em centavos) e **lançamentos
  recorrentes** (mensal/semanal/anual, geração idempotente de pendências).
- **Cartões de crédito** — modelados separadamente de contas bancárias, com
  fatura calculada a partir do dia de fechamento/vencimento, pagamento
  integral ou parcial, e limite utilizado/disponível.
- **Categorização automática** — regras configuráveis (contém / começa com
  / igual), por prioridade.
- **Importação de extratos** — CSV (com detecção de delimitador/codificação
  e mapeamento de colunas) e OFX, com detecção de duplicidade antes de
  importar.
- **Visão Geral** — saldos, receitas/despesas do período, despesas por
  categoria, evolução mensal e indicadores de cartões (faturas
  abertas/a vencer, limite utilizado).
- **Metas financeiras** e **Simulador** (tempo para atingir uma meta,
  aporte mensal necessário, projeção de saldo).

## Stack

- [Streamlit](https://streamlit.io/) — interface
- [PostgreSQL](https://www.postgresql.org/) (testado com [Supabase](https://supabase.com/)) — banco de dados
- [SQLAlchemy](https://www.sqlalchemy.org/) — acesso a dados (SQL explícito, sem ORM declarativo)
- [Alembic](https://alembic.sqlalchemy.org/) — migrations
- [Plotly](https://plotly.com/python/) — gráficos
- [pandas](https://pandas.pydata.org/) — leitura de CSV
- [ofxparse](https://github.com/jseutter/ofxparse) — leitura de OFX
- [pytest](https://docs.pytest.org/) — testes automatizados

## Requisitos

- Python 3.11+
- Uma instância PostgreSQL acessível (local, Supabase, ou outro provedor)

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

Copie o arquivo de exemplo e preencha com sua conexão real:

```bash
cp .env.example .env
```

Edite `.env` e configure a variável `DATABASE_URL`:

```
DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

> O `.env` nunca deve ser commitado — ele já está no `.gitignore`.

Em produção (ex.: Streamlit Community Cloud), a mesma variável pode ser
definida em `.streamlit/secrets.toml` (também ignorado pelo git) em vez de
`.env`; o `app.py` lê de `st.secrets` automaticamente quando `DATABASE_URL`
não está definida localmente.

### 4. Rodar as migrations

Com o banco acessível e o `.env` configurado:

```bash
alembic upgrade head
```

Isso cria todas as tabelas necessárias (`contas`, `categorias`,
`transacoes`, `regras_categorizacao`, `metas`, `recorrencias`, `cartoes`,
`faturas_cartao`, `pagamentos_fatura`).

Para conferir a revisão atual do banco:

```bash
alembic current
```

### 5. Executar o Streamlit

```bash
streamlit run app.py
```

O app abre em `http://localhost:8501` por padrão.

## Rodando os testes

```bash
pytest
```

Os testes usam o mesmo banco configurado em `DATABASE_URL` — cada teste cria
seus próprios dados e os remove ao final (via fixtures ou blocos
`try/finally`), sem deixar resíduos. **Recomendado rodar contra um banco de
desenvolvimento, não contra dados reais.**

Para rodar só um arquivo específico:

```bash
pytest tests/test_faturas.py -v
```

## Estrutura do projeto

```
finance_app/
├── app.py                  # ponto de entrada do Streamlit (navegação + página Início)
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.example
├── migrations/
│   └── versions/           # uma migration por alteração de schema
├── pages/                  # uma página Streamlit por arquivo
│   ├── 1_Visao_Geral.py
│   ├── 2_Lancamentos.py    # inclui parcelamento e recorrências
│   ├── 3_Contas.py
│   ├── 4_Categorias.py     # inclui regras de categorização
│   ├── 5_Importacao.py     # CSV e OFX
│   ├── 6_Metas.py
│   ├── 7_Simulador.py
│   └── 8_Cartoes.py
├── src/                    # toda a lógica de negócio e acesso a dados
│   ├── banco_de_dados.py   # engine SQLAlchemy, leitura de DATABASE_URL
│   ├── contas.py / categorias.py / transacoes.py
│   ├── categorizador.py    # regras de categorização automática
│   ├── recorrencias.py
│   ├── cartoes.py / faturas.py
│   ├── importador.py       # pipeline compartilhado CSV/OFX (parsing, duplicidade)
│   ├── ofx.py / graficos.py / formatacao.py / datas.py
│   ├── resumo_financeiro.py
│   ├── metas.py / simulador.py
└── tests/                  # suíte pytest (um arquivo por módulo de src/)
```

As páginas (`pages/`) não executam SQL diretamente — toda a lógica fica em
`src/`, o que também é o que torna os testes possíveis sem precisar do
Streamlit.

## Preparação para deploy

O projeto não tem dependências de caminhos absolutos locais; toda
configuração de banco vem de `DATABASE_URL` (via `.env` localmente ou via
`st.secrets`/variável de ambiente em produção). Para implantar:

1. Provisionar um PostgreSQL (ex.: Supabase) e definir `DATABASE_URL` no
   ambiente de destino.
2. Rodar `alembic upgrade head` apontando para esse banco (pode ser feito
   de qualquer máquina com acesso à rede e `DATABASE_URL` configurada —
   não precisa ser a mesma máquina do deploy do Streamlit).
3. Publicar com `streamlit run app.py` (ou o equivalente do serviço de
   hospedagem escolhido).

Nenhum segredo fica no código-fonte; `.env`, `.env.*` (exceto
`.env.example`) e `.streamlit/secrets.toml` estão no `.gitignore`.

## Ainda não implementado (planejado para V2)

Open Finance/API bancária, investimentos complexos, cotação de
ações/cripto, IA e recomendações automáticas, notificações, autenticação
multiusuário, compartilhamento de contas, orçamento familiar e conciliação
bancária avançada.
