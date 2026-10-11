from datetime import date

from sqlalchemy.exc import IntegrityError

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
        birth_date = self._parse_birth_date(
            client_data["birth_date"]
        )

        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        if (
            self.client_repository.get_by_document_number(
                document_number
            )
            is not None
        ):
            raise DuplicatedDocumentNumber(document_number)

        age = self._age_in_years(birth_date)

        if age < MINIMUM_AGE:
            raise UnderageClient(age, MINIMUM_AGE)

        if age > MAXIMUM_AGE:
            raise InvalidBirthdate(client_data["birth_date"])

        client = self.client_repository.create(client_data)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

            if (
                self.client_repository.get_by_document_number(
                    document_number
                )
                is not None
            ):
                raise DuplicatedDocumentNumber(document_number)

            raise

        return {
            "client_key": str(client.client_key)
        }

    def _parse_birth_date(self, raw_birth_date: str) -> date:
        try:
            birth_date = date.fromisoformat(raw_birth_date)
        except ValueError:
            raise InvalidBirthdate(raw_birth_date)

        if birth_date > date.today():
            raise InvalidBirthdate(raw_birth_date)

        return birth_date

    def _age_in_years(self, birth_date: date) -> int:
        today = date.today()
        age = today.year - birth_date.year

        if (
            today.month,
            today.day,
        ) < (
            birth_date.month,
            birth_date.day,
        ):
            age -= 1

        return age