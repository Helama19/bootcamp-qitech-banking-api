from errors import QIException


class NotFoundSampleEntity(QIException):
    code = "QIT001001"

    def __init__(self, sample_entity_key) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = (
            f"There is already an entity with the document number {document_number}."
        )
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageSampleEntity(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = (
            f"The entity is {age} years old, and the minimum is {minimum_age}."
        )
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


# ------------------------------------------------------------------
# Erros do domínio bancário
# ------------------------------------------------------------------

class UnderageClient(QIException):
    code = "QIT002001"

    def __init__(self, age, minimum_age) -> None:
        title = "Client is underage"
        http_status = 422
        description = (
            f"The client is {age} years old, and the minimum is {minimum_age}."
        )
        translation = (
            f"É preciso ter pelo menos {minimum_age} anos para criar uma conta."
        )
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundClient(QIException):
    code = "QIT002002"

    def __init__(self, client_key) -> None:
        title = "Client not found"
        http_status = 404
        description = f"Client with key {client_key} was not found."
        translation = "O cliente informado não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class ClientAlreadyHasAccount(QIException):
    code = "QIT002003"

    def __init__(self, client_key) -> None:
        title = "Client already has an account"
        http_status = 409
        description = f"Client with key {client_key} already has an account."
        translation = "O cliente informado já possui uma conta."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundAccount(QIException):
    code = "QIT002004"

    def __init__(self, account_key) -> None:
        title = "Account not found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = "A conta informada não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class AccountCannotReceive(QIException):
    code = "QIT002005"

    def __init__(self, account_key, status) -> None:
        title = "Account cannot receive funds"
        http_status = 422
        description = (
            f"Account {account_key} with status {status} cannot receive funds."
        )
        translation = "A conta informada não pode receber valores."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidTransactionAmount(QIException):
    code = "QIT002006"

    def __init__(self, amount) -> None:
        title = "Invalid transaction amount"
        http_status = 422
        description = f"The transaction amount {amount} must be greater than zero."
        translation = "O valor da transação deve ser maior que zero."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyConflict(QIException):
    code = "QIT002007"

    def __init__(self, idempotency_key) -> None:
        title = "Idempotency key conflict"
        http_status = 409
        description = (
            f"Idempotency key {idempotency_key} was already used "
            "for a different operation."
        )
        translation = (
            "A chave de idempotência já foi utilizada em uma operação diferente."
        )
        super().__init__(title, self.code, http_status, description, translation)


class AccountCannotSend(QIException):
    code = "QIT002008"

    def __init__(self, account_key, status) -> None:
        title = "Account cannot send funds"
        http_status = 422
        description = (
            f"Account {account_key} with status {status} cannot send funds."
        )
        translation = "A conta de origem não pode enviar valores."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientBalance(QIException):
    code = "QIT002009"

    def __init__(self, account_key) -> None:
        title = "Insufficient balance"
        http_status = 422
        description = (
            f"Account {account_key} does not have sufficient balance "
            "for this transaction."
        )
        translation = "A conta de origem não possui saldo suficiente."
        super().__init__(title, self.code, http_status, description, translation)


class SameAccountTransfer(QIException):
    code = "QIT002010"

    def __init__(self, account_key) -> None:
        title = "Invalid transfer accounts"
        http_status = 422
        description = (
            f"Account {account_key} cannot be both the source "
            "and destination of a transfer."
        )
        translation = (
            "A conta de origem e a conta de destino devem ser diferentes."
        )
        super().__init__(title, self.code, http_status, description, translation)


class AccountCannotChangeStatus(QIException):
    code = "QIT002011"

    def __init__(self, current_status, new_status) -> None:
        title = "Account cannot change status"
        http_status = 422
        description = (
            f"Account with status {current_status} cannot change "
            f"to status {new_status}."
        )
        translation = (
            "Uma conta encerrada não pode ter seu status alterado."
        )
        super().__init__(title, self.code, http_status, description, translation)


class AccountMustHaveZeroBalance(QIException):
    code = "QIT002012"

    def __init__(self, account_key) -> None:
        title = "Account must have zero balance"
        http_status = 422
        description = (
            f"Account {account_key} must have zero balance before being closed."
        )
        translation = (
            "A conta precisa estar com saldo zero para ser encerrada."
        )
        super().__init__(title, self.code, http_status, description, translation)