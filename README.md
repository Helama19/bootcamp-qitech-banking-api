# Bootcamp QI Tech — Banking API

API REST desenvolvida como projeto do Bootcamp QI Tech.

O projeto implementa as operações essenciais de um banco digital, incluindo cadastro de clientes, criação e gerenciamento de contas, depósitos, transferências com tarifa, consulta de saldo e extrato paginado.

A aplicação foi desenvolvida em **Python + FastAPI**, utiliza **PostgreSQL** como banco de dados e é executada com **Docker**.

---

## Funcionalidades

A API permite:

- cadastrar clientes;
- criar uma conta vinculada a um cliente;
- consultar o saldo de uma conta;
- realizar depósitos;
- realizar transferências entre contas;
- cobrar tarifa nas transferências;
- consultar extrato paginado;
- bloquear, desbloquear e encerrar contas;
- proteger operações contra duplicidade por meio de idempotência;
- controlar concorrência em operações financeiras.

### Regras principais

- Cada cliente pode possuir apenas uma conta.
- O cliente deve possuir CPF válido e ter pelo menos 18 anos.
- Contas começam com saldo `0.00` e status `active`.
- Uma conta `blocked` pode receber valores e ser consultada, mas não pode enviar transferências.
- Uma conta `closed` não pode receber nem enviar valores.
- Uma conta só pode ser encerrada quando seu saldo for zero.
- O status `closed` é definitivo.
- O saldo de uma conta nunca pode ficar negativo.
- Depósitos e transferências exigem uma chave de idempotência.
- Transferências cobram uma tarifa de **1%** sobre o valor transferido.
- A conta de origem paga o valor da transferência mais a tarifa.
- A conta de destino recebe somente o valor transferido.
- Valores monetários são representados com duas casas decimais e limitados à capacidade de `NUMERIC(15, 2)`.
- O maior valor monetário representável pela aplicação é `9999999999999.99`.
- Uma operação é rejeitada caso faça o saldo resultante ultrapassar esse limite.
- Em transferências, o valor total debitado, incluindo a tarifa, também deve respeitar o limite monetário.

---

## Tecnologias

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker / Docker Compose
- Pytest
- JSON Schema

---

## Arquitetura

O projeto separa as responsabilidades em camadas:

```text
requisição HTTP
      ↓
   Resource
      ↓
  Controller
      ↓
 Repository
      ↓
 PostgreSQL
```

### Estrutura

```text
src/
├── app.py
├── constants.py
├── database.py
├── controllers/
├── errors/
├── middlewares/
├── models/
├── repositories/
├── resources/
├── schemas/
└── utils/

database/
└── database.sql

tests/
└── integration/
```

### Resources

Responsáveis pela interface HTTP da aplicação. Recebem os dados da requisição, acionam o controller correspondente e constroem a resposta HTTP.

### Controllers

Concentram as regras de negócio, como validação de idade, controle de status das contas, saldo suficiente, cálculo da tarifa, limites monetários e idempotência.

### Repositories

Concentram o acesso ao banco de dados por meio do SQLAlchemy.

Também são responsáveis pelas consultas que utilizam bloqueio pessimista durante operações financeiras concorrentes.

### Models

Representam as entidades persistidas no PostgreSQL.

---

## Banco de dados

As principais entidades são:

- `client`
- `account`
- `account_status`
- `financial_transaction`
- `transaction_type`

Valores monetários são armazenados com `NUMERIC(15, 2)`, permitindo no máximo 13 dígitos na parte inteira e 2 casas decimais.

A aplicação valida esses limites antes de persistir operações financeiras.

O saldo atual é armazenado diretamente na conta e atualizado na mesma transação de banco que registra a operação financeira.

### Tipos de transação

Existem dois tipos:

```text
deposit
transfer
```

A tarifa da transferência é armazenada no próprio registro da transferência.

---

## Transferências e tarifa

Cada transferência possui uma tarifa de **1%**:

```text
tarifa = valor × 0,01
```

A tarifa é calculada utilizando `Decimal` e arredondada para centavos com `ROUND_HALF_UP`.

Por exemplo, uma transferência de:

```text
R$ 100,00
```

gera:

```text
Valor transferido: R$ 100,00
Tarifa:             R$   1,00
Total debitado:     R$ 101,00
```

A conta de destino recebe `R$ 100,00`.

A transferência somente é realizada quando a conta de origem possui saldo suficiente para pagar tanto o valor transferido quanto a tarifa.

O valor total debitado e o saldo resultante da conta de destino também precisam respeitar o limite monetário suportado pelo banco de dados.

---

## Concorrência

Operações financeiras utilizam bloqueio pessimista no PostgreSQL por meio de `SELECT ... FOR UPDATE`.

Durante um depósito, a conta é bloqueada antes da atualização do saldo.

Durante transferências, as duas contas envolvidas são bloqueadas em ordem determinística pelo identificador interno.

Isso evita condições de corrida, perda de atualizações e reduz o risco de deadlock quando existem operações concorrentes.

A atualização dos saldos e a criação da transação financeira acontecem dentro da mesma transação de banco de dados.

Caso a operação falhe, é realizado rollback e nenhuma alteração parcial deve permanecer persistida.

As restrições `UNIQUE` do banco também funcionam como garantia final em cenários concorrentes, como duas tentativas simultâneas de cadastrar o mesmo CPF, criar duas contas para o mesmo cliente ou utilizar a mesma chave de idempotência.

---

## Idempotência

Depósitos e transferências recebem uma `idempotency_key`.

A mesma operação enviada novamente com a mesma chave não movimenta dinheiro uma segunda vez.

Se a mesma chave for reutilizada com dados diferentes, a API retorna conflito.

O banco também possui uma restrição `UNIQUE` sobre a chave de idempotência como garantia final contra duplicidade.

Em um retry válido, a API retorna a transação originalmente associada à chave de idempotência, sem executar novamente a movimentação.

Os campos referentes à operação, como `transaction_key`, valor e tarifa, permanecem associados à transação original. Os campos de saldo representam o saldo atual da conta no momento da resposta e podem, portanto, ser diferentes dos retornados na primeira requisição caso tenham ocorrido movimentações posteriores.

---

## Status das contas

Uma conta pode assumir três estados:

| Status | Receber | Transferir | Consultar |
|---|---:|---:|---:|
| `active` | Sim | Sim | Sim |
| `blocked` | Sim | Não | Sim |
| `closed` | Não | Não | Sim |

Uma conta só pode ser encerrada com saldo zero.

Depois de encerrada, ela não pode retornar para outro status.

---

## Rotas

As rotas de negócio exigem o header:

```text
INTERNAL-TOKEN: default_token
```

As rotas `/` e `/health_check` são públicas.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Identificação do serviço |
| `GET` | `/health_check` | Health check |
| `POST` | `/clients` | Cadastro de cliente |
| `POST` | `/accounts` | Criação de conta |
| `GET` | `/accounts/{account_key}/balance` | Consulta de saldo |
| `GET` | `/accounts/{account_key}/statement` | Extrato paginado |
| `PATCH` | `/accounts/{account_key}/status` | Alteração do status |
| `POST` | `/deposits` | Depósito |
| `POST` | `/transfers` | Transferência |

---

## Executando o projeto

### Pré-requisitos

É necessário possuir:

- Docker;
- Docker Compose;
- Git.

Para executar os testes localmente também é necessário Python 3.11.

### Subindo a aplicação

Na raiz do projeto:

```bash
docker compose up
```

A API ficará disponível em:

```text
http://localhost:3000
```

Para verificar se está funcionando:

```text
GET http://localhost:3000/health_check
```

A resposta esperada é:

```text
204 No Content
```

### Encerrando

```bash
docker compose down
```

Para apagar também o volume do PostgreSQL:

```bash
docker compose down -v
```

---

## Recriando o banco de dados

O schema inicial está em:

```text
database/database.sql
```

O arquivo é executado quando o banco é criado.

Caso o schema seja alterado durante o desenvolvimento, o banco pode ser reconstruído com:

```bash
docker compose down -v
docker compose build --no-cache db
docker compose up
```

> O comando `down -v` remove os dados armazenados no banco local.

---

## Executando os testes

Os testes de integração executam requisições HTTP contra a API rodando no Docker.

Instale as dependências de desenvolvimento:

```bash
python -m pip install -r requirements-dev.txt
```

Com a API e o banco em execução:

```bash
python -m pytest -q
```

No ambiente utilizado durante o desenvolvimento, a suíte final possui:

```text
157 passed
```

Os testes cobrem, entre outros cenários:

- cadastro e validação de clientes;
- criação de contas;
- depósitos;
- transferências;
- cálculo e arredondamento da tarifa;
- saldo insuficiente;
- limites e overflow de valores monetários;
- status das contas;
- extrato e paginação;
- idempotência e retries após movimentações posteriores;
- operações financeiras concorrentes;
- cadastros concorrentes de clientes e contas;
- prevenção de `lost update`;
- prevenção de movimentações duplicadas;
- transferências em sentidos opostos sem deadlock.

Os testes concorrentes verificam tanto operações financeiras quanto restrições de unicidade da aplicação.

Entre os cenários cobertos estão depósitos simultâneos na mesma conta, transferências disputando o mesmo saldo, requisições simultâneas com a mesma chave de idempotência, criação concorrente de clientes com o mesmo CPF e criação concorrente de contas para o mesmo cliente.

---

## Exemplos

### Criar cliente

```http
POST /clients
INTERNAL-TOKEN: default_token
Content-Type: application/json
```

```json
{
  "name": "Maria da Silva",
  "document_number": "52998224725",
  "birth_date": "1990-05-17"
}
```

### Criar conta

```http
POST /accounts
INTERNAL-TOKEN: default_token
Content-Type: application/json
```

```json
{
  "client_key": "<client_key>"
}
```

### Realizar depósito

```http
POST /deposits
INTERNAL-TOKEN: default_token
Content-Type: application/json
```

```json
{
  "account_key": "<account_key>",
  "amount": "100.00",
  "idempotency_key": "<uuid>"
}
```

### Realizar transferência

```http
POST /transfers
INTERNAL-TOKEN: default_token
Content-Type: application/json
```

```json
{
  "source_account_key": "<source_account_key>",
  "destination_account_key": "<destination_account_key>",
  "amount": "50.00",
  "idempotency_key": "<uuid>"
}
```

Para uma transferência de `50.00`, a tarifa de 1% corresponde a `0.50`, portanto a conta de origem precisa possuir pelo menos `50.50`.

### Consultar saldo

```http
GET /accounts/<account_key>/balance
INTERNAL-TOKEN: default_token
```

### Consultar extrato

```http
GET /accounts/<account_key>/statement?page=1&page_size=20
INTERNAL-TOKEN: default_token
```

O extrato informa se cada movimentação representa entrada (`IN`) ou saída (`OUT`) para a conta consultada.

---

## Segurança e observabilidade

As rotas de negócio são protegidas por um token interno enviado por header.

Cada requisição também recebe um `X-Request-ID`, utilizado para correlacionar os logs da aplicação.

O projeto não registra o corpo completo das requisições nos logs.

---

## Decisões de projeto

Algumas decisões foram tomadas para manter a implementação simples, consistente e segura dentro do escopo do projeto.

O saldo atual é persistido diretamente na entidade `account`. O histórico financeiro é mantido em `financial_transaction`.

Uma transferência é representada por uma única transação contendo conta de origem, conta de destino, valor e tarifa. O modelo não pretende implementar um ledger contábil completo de partidas dobradas.

`Decimal` é utilizado nas regras financeiras para evitar cálculos monetários com ponto flutuante.

O PostgreSQL utiliza `NUMERIC(15, 2)` para persistência dos valores.

A consistência concorrente das movimentações financeiras é garantida por transações de banco e bloqueio pessimista das contas envolvidas.

Restrições `UNIQUE` no banco funcionam como última linha de defesa para regras que também são verificadas pela aplicação, como CPF único, uma conta por cliente e chave de idempotência única.

---

## Licença

Este projeto utiliza a licença MIT. Consulte o arquivo `LICENSE`.