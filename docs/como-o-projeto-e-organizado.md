# Como o projeto é organizado

Este documento apresenta a organização da API Bancária desenvolvida para o Bootcamp QI Tech 2026.

A aplicação foi estruturada em camadas para separar as responsabilidades de entrada HTTP, regras de negócio, acesso ao banco de dados e persistência.

O fluxo principal de uma requisição é:

```text
Requisição HTTP
      ↓
Middlewares
      ↓
Resources
      ↓
Schemas
      ↓
Controllers
      ↓
Repositories
      ↓
Models
      ↓
PostgreSQL
```

Cada camada possui uma responsabilidade específica. Essa separação evita que regras de negócio, consultas ao banco e tratamento HTTP fiquem misturados no mesmo ponto da aplicação.

---

## 1. Fluxo de uma requisição

As operações bancárias seguem, de forma geral, o mesmo caminho.

### Middlewares

Os middlewares executam tarefas comuns às requisições, como:

- validação do `INTERNAL-TOKEN`;
- identificação da requisição;
- logging;
- gerenciamento do contexto e da sessão de banco de dados.

Caso o `INTERNAL-TOKEN` esteja ausente ou incorreto, a requisição é interrompida com HTTP `403`.

### Resources

Os arquivos em `src/resources/` definem as rotas HTTP da aplicação.

Eles recebem a requisição, acionam a validação do payload quando necessário, chamam o controller correspondente e devolvem a resposta HTTP.

As principais operações disponíveis são:

- criação de clientes;
- criação de contas;
- depósitos;
- transferências;
- consulta de saldo;
- consulta de extrato;
- alteração do status da conta.

As regras financeiras não ficam nessa camada.

### Schemas

Os arquivos em `src/schemas/` definem, por meio de JSON Schema, o formato aceito nos corpos das requisições.

Essa camada verifica aspectos estruturais, como:

- campos obrigatórios;
- tipos;
- formatos;
- quantidade de casas decimais;
- presença de campos não permitidos.

Payloads que não respeitam o contrato são rejeitados antes da execução da regra de negócio.

### Controllers

Os controllers concentram as regras de negócio da aplicação.

É nessa camada que são verificadas condições como:

- validade do CPF;
- idade permitida para cadastro;
- existência de cliente ou conta;
- status da conta;
- saldo disponível;
- limite monetário;
- tarifa de transferência;
- idempotência;
- regras para encerramento de conta.

Os controllers também coordenam as transações de banco de dados e determinam quando uma operação pode ser confirmada com `commit` ou precisa ser revertida com `rollback`.

### Repositories

Os repositories concentram o acesso ao banco de dados.

Eles realizam consultas e operações de persistência utilizadas pelos controllers, mantendo SQL e detalhes de acesso aos dados separados das regras de negócio.

### Models

Os arquivos em `src/models/` representam as entidades persistidas no PostgreSQL por meio do SQLAlchemy.

Entre as principais entidades estão:

- cliente;
- conta;
- status da conta;
- transação financeira;
- tipo da transação.

O schema inicial do PostgreSQL é definido em `database/database.sql`.

---

## 2. Responsabilidade de cada camada

| Camada | Responsabilidade |
|---|---|
| `resources/` | Definir as rotas HTTP e encaminhar as requisições |
| `schemas/` | Validar o formato dos payloads de entrada |
| `controllers/` | Aplicar regras de negócio e coordenar transações |
| `repositories/` | Consultar e persistir dados |
| `models/` | Representar as entidades do banco |
| `errors/` | Definir os erros utilizados pela aplicação |
| `middlewares/` | Executar comportamentos comuns às requisições |
| `utils/` | Disponibilizar funções auxiliares de uso geral |

A dependência principal segue um único sentido:

```text
resources → controllers → repositories → models
```

Um repository não decide se uma transferência é permitida, por exemplo. Ele apenas executa a operação de persistência solicitada pelo controller.

---

## 3. Organização das operações bancárias

### Clientes

O cadastro de clientes valida as regras necessárias antes da persistência.

O CPF deve ser válido e único. A aplicação também valida a data de nascimento e os limites de idade definidos pela regra de negócio.

Além da verificação realizada pela aplicação, o banco possui restrição `UNIQUE` para impedir duplicidade de CPF mesmo quando duas requisições concorrentes tentam cadastrar o mesmo documento.

### Contas

Cada cliente pode possuir apenas uma conta.

A conta mantém o saldo corrente e possui um status que determina quais operações são permitidas:

- `ACTIVE`: pode receber, enviar e consultar;
- `BLOCKED`: pode receber e consultar, mas não pode enviar;
- `CLOSED`: não pode receber nem enviar, mas seu histórico continua disponível.

Uma conta somente pode ser encerrada quando seu saldo é zero.

O banco também possui uma restrição `UNIQUE` para garantir que um mesmo cliente não receba duas contas em situações concorrentes.

### Depósitos

O depósito utiliza uma `idempotency_key`.

Se uma requisição for repetida com a mesma chave e os mesmos dados, a movimentação não é executada novamente. A API recupera a operação já existente.

Se a mesma chave for reutilizada com dados diferentes, a requisição é tratada como conflito.

Antes de alterar o saldo, a conta é bloqueada no banco com `SELECT FOR UPDATE`. Isso impede que depósitos concorrentes sobrescrevam o saldo uns dos outros.

### Transferências

Uma transferência envolve:

- conta de origem;
- conta de destino;
- valor transferido;
- tarifa;
- atualização dos dois saldos;
- registro da transação.

A tarifa corresponde a 1% do valor transferido e é calculada utilizando `Decimal`, com arredondamento `ROUND_HALF_UP`.

A conta de origem paga:

```text
valor da transferência + tarifa
```

A conta de destino recebe:

```text
valor da transferência
```

Todas essas alterações pertencem à mesma transação no PostgreSQL.

Se qualquer validação falhar, nenhuma alteração parcial é confirmada.

---

## 4. Concorrência e atomicidade

Operações financeiras exigem cuidados adicionais porque duas requisições podem acessar as mesmas contas simultaneamente.

A aplicação utiliza bloqueio pessimista com:

```sql
SELECT ... FOR UPDATE
```

Antes de atualizar um saldo, a linha correspondente é bloqueada.

Dessa forma, uma segunda requisição que tente modificar a mesma conta precisa esperar a primeira terminar. Quando conseguir o lock, ela verá o saldo já atualizado.

Isso evita problemas como:

- `lost update`;
- `double-spend`;
- decisões tomadas com base em saldo desatualizado.

Nas transferências, as contas envolvidas são bloqueadas em ordem determinística pelo `Account.id`.

Essa estratégia evita que duas transferências opostas adquiram os locks em ordens diferentes e criem uma espera circular.

---

## 5. Idempotência

Depósitos e transferências exigem uma `idempotency_key`.

A idempotência é protegida em duas camadas.

Na aplicação, o controller verifica se já existe uma operação com aquela chave.

No banco, uma restrição `UNIQUE` funciona como proteção final contra duas requisições concorrentes que utilizem a mesma chave.

Quando duas requisições idênticas chegam simultaneamente, apenas uma movimentação financeira pode ser persistida.

Se ocorrer uma disputa na gravação, a requisição que perder a corrida executa `rollback`, recupera a operação já criada e devolve o resultado correspondente sem movimentar o dinheiro novamente.

---

## 6. Valores monetários

Valores financeiros são representados com `Decimal` na aplicação e `NUMERIC(15,2)` no PostgreSQL.

O maior valor monetário representável é:

```text
9999999999999.99
```

A aplicação valida tanto o valor solicitado quanto o saldo resultante da operação.

Isso evita:

- perda de precisão causada por `float`;
- valores com casas decimais inválidas;
- saldo negativo;
- overflow da coluna monetária.

---

## 7. Banco de dados

O arquivo:

```text
database/database.sql
```

define o schema utilizado quando o banco PostgreSQL é criado.

Caso esse arquivo seja alterado depois que o volume do banco já existe, é necessário recriar o volume para aplicar novamente o schema inicial:

```bash
docker compose down -v
docker compose up -d --build
```

Esse comando remove os dados existentes no volume local.

Em um ambiente de produção, alterações de schema normalmente seriam realizadas por migrations. Para o escopo deste projeto, o schema inicial versionado é suficiente.

---

## 8. Testes

Os testes estão organizados em `tests/` e cobrem tanto regras funcionais quanto cenários de integração e concorrência.

Entre os cenários testados estão:

- cadastro de clientes;
- criação de contas;
- depósitos;
- transferências;
- cálculo da tarifa;
- consulta de saldo;
- extrato;
- alteração de status;
- idempotência;
- limites monetários;
- cadastros concorrentes;
- depósitos simultâneos;
- transferências concorrentes;
- prevenção de `double-spend`;
- transferências opostas sem deadlock.

A suíte pode ser executada com:

```bash
pytest
```

O projeto também foi validado a partir de um clone limpo, utilizando os serviços definidos no Docker Compose.

---

## 9. Executando o projeto

Com Docker e Docker Compose disponíveis:

```bash
docker compose up -d --build
```

A API é disponibilizada na porta `3000`, e o PostgreSQL é iniciado como serviço do mesmo ambiente.

Para acompanhar os containers:

```bash
docker compose ps
```

Para encerrar:

```bash
docker compose down
```

---

## 10. Resumo da arquitetura

A ideia central da organização é manter cada responsabilidade no lugar adequado:

```text
HTTP
 ↓
resources
 ↓
controllers
 ↓
repositories
 ↓
models
 ↓
PostgreSQL
```

Os schemas protegem o contrato de entrada, os middlewares tratam comportamentos comuns às requisições e os controllers concentram as decisões de negócio.

Para as operações financeiras, PostgreSQL, transações atômicas, `SELECT FOR UPDATE`, restrições `UNIQUE` e chaves de idempotência trabalham em conjunto para manter o estado consistente mesmo diante de requisições simultâneas ou repetidas.
