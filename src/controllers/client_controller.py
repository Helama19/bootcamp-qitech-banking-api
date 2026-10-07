from datetime import date

from controllers.base_controller import BaseController
from errors import (
    DuplicatedDocumentNumber,
    InvalidBirthdate,
    InvalidDocumentNumber,
    UnderageClient,
)
from repositories import ClientRepository
from utils.document_number import is_valid_cpf


MINIMUM_AGE = 18
MAXIMUM_AGE = 120


class ClientController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)

    def create(self, client_data: dict) -> dict:
        self.logger.debug("Criando um novo cliente")

        document_number = client_data["document_number"]
        birth_date = self._parse_birth_date(client_data["birth_date"])

        # O schema já garante que recebemos 11 dígitos.
        # Aqui verificamos se esses dígitos formam um CPF válido.
        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        # Cada CPF pode possuir somente um cadastro.
        if (
            self.client_repository.get_by_document_number(document_number)
            is not None
        ):
            raise DuplicatedDocumentNumber(document_number)

        age = self._age_in_years(birth_date)

        # O produto é destinado somente a maiores de idade.
        if age < MINIMUM_AGE:
            raise UnderageClient(age, MINIMUM_AGE)

        # Datas que implicariam idade superior a 120 anos são
        # consideradas dados inconsistentes.
        if age > MAXIMUM_AGE:
            raise InvalidBirthdate(client_data["birth_date"])

        client = self.client_repository.create(client_data)

        self.session.commit()

        return {
            "client_key": str(client.client_key)
        }

    def _parse_birth_date(self, raw_birth_date: str) -> date:
        try:
            birth_date = date.fromisoformat(raw_birth_date)
        except ValueError:
            raise InvalidBirthdate(raw_birth_date)

        # Uma data de nascimento não pode estar no futuro.
        if birth_date > date.today():
            raise InvalidBirthdate(raw_birth_date)

        return birth_date

    def _age_in_years(self, birth_date: date) -> int:
        today = date.today()

        age = today.year - birth_date.year

        # Se a pessoa ainda não fez aniversário neste ano,
        # descontamos um ano.
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1

        return age