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

Concentram as regras de negócio, como validação de idade, controle de status das contas, saldo suficiente, cálculo da tarifa e idempotência.

### Repositories

Concentram o acesso ao banco de dados por meio do SQLAlchemy.

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

Valores monetários são armazenados com `NUMERIC(15, 2)`.

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

A tarifa é arredondada para centavos.

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

---

## Concorrência

Operações financeiras utilizam bloqueio pessimista no PostgreSQL por meio de `SELECT ... FOR UPDATE`.

Durante transferências, as duas contas envolvidas são bloqueadas em ordem determinística pelo identificador interno.

Isso evita condições de corrida e reduz o risco de deadlock quando existem transferências concorrentes.

A atualização dos saldos e a criação da transação financeira acontecem dentro da mesma transação de banco de dados.

Caso a operação falhe, é realizado rollback e nenhuma alteração parcial deve permanecer persistida.

---

## Idempotência

Depósitos e transferências recebem uma `idempotency_key`.

A mesma operação enviada novamente com a mesma chave não movimenta dinheiro uma segunda vez.

Se a mesma chave for reutilizada com dados diferentes, a API retorna conflito.

O banco também possui uma restrição `UNIQUE` sobre a chave de idempotência como garantia final contra duplicidade.

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
146 passed
```

Os testes cobrem, entre outros cenários:

- cadastro e validação de clientes;
- criação de contas;
- depósitos;
- transferências;
- cálculo da tarifa;
- saldo insuficiente;
- status das contas;
- extrato e paginação;
- idempotência;
- operações financeiras concorrentes.

Também existem testes concorrentes para verificar que requisições simultâneas não provoquem movimentações duplicadas ou inconsistência de saldo.

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
  "destination_account_key": "<account_key>",
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

## Licença

Este projeto utiliza a licença MIT. Consulte o arquivo `LICENSE`.