from datetime import date, timedelta

import pytest

from tests.utils import RandomGenerator, RequestGenerator


class TestClient:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _birth_date_for_age(age: int) -> str:
        today = date.today()

        try:
            birth_date = today.replace(year=today.year - age)
        except ValueError:
            # Caso especial: 29 de fevereiro.
            birth_date = today.replace(
                year=today.year - age,
                day=28,
            )

        return birth_date.isoformat()

    @staticmethod
    def _valid_payload() -> dict:
        return {
            "name": "Cliente Teste",
            "document_number": TestClient._cpf_without_mask(),
            "birth_date": "2000-01-01",
        }

    def test_create_valid_client(self):
        payload = self._valid_payload()

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        assert "client_key" in response
        assert response["client_key"] is not None

    def test_duplicate_cpf_is_rejected(self):
        cpf = self._cpf_without_mask()

        first_payload = {
            "name": "Primeiro Cliente",
            "document_number": cpf,
            "birth_date": "2000-01-01",
        }

        second_payload = {
            "name": "Segundo Cliente",
            "document_number": cpf,
            "birth_date": "1995-05-10",
        }

        first_status, first_response = RequestGenerator.POST_client(
            first_payload
        )

        second_status, second_response = RequestGenerator.POST_client(
            second_payload
        )

        assert first_status == 201
        assert "client_key" in first_response

        assert second_status == 409
        assert "code" in second_response

    @pytest.mark.parametrize(
        "document_number",
        [
            "11111111111",
            "00000000000",
            "12345678901",
            "99999999999",
        ],
    )
    def test_invalid_cpf_check_digits_are_rejected(
        self,
        document_number: str,
    ):
        payload = {
            "name": "CPF Invalido",
            "document_number": document_number,
            "birth_date": "2000-01-01",
        }

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert "code" in response

    @pytest.mark.parametrize(
        "document_number",
        [
            "1234567890",
            "123456789012",
            "123.456.789-09",
            "abcdefghijk",
            "1234567890a",
            "",
        ],
    )
    def test_invalid_cpf_format_is_rejected(
        self,
        document_number: str,
    ):
        payload = {
            "name": "CPF Formato Invalido",
            "document_number": document_number,
            "birth_date": "2000-01-01",
        }

        status, _ = RequestGenerator.POST_client(payload)

        assert status == 400

    def test_underage_client_is_rejected(self):
        payload = self._valid_payload()
        payload["birth_date"] = self._birth_date_for_age(17)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert "code" in response

    def test_exactly_eighteen_year_old_client_is_accepted(self):
        payload = self._valid_payload()
        payload["birth_date"] = self._birth_date_for_age(18)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        assert "client_key" in response

    def test_future_birth_date_is_rejected(self):
        tomorrow = date.today() + timedelta(days=1)

        payload = self._valid_payload()
        payload["birth_date"] = tomorrow.isoformat()

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert "code" in response

    def test_client_older_than_120_is_rejected(self):
        payload = self._valid_payload()
        payload["birth_date"] = self._birth_date_for_age(121)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert "code" in response

    def test_exactly_120_year_old_client_is_accepted(self):
        payload = self._valid_payload()
        payload["birth_date"] = self._birth_date_for_age(120)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        assert "client_key" in response

    @pytest.mark.parametrize(
        "birth_date",
        [
            "2000-13-01",
            "2000-02-30",
            "not-a-date",
            "01-01-2000",
        ],
    )
    def test_invalid_birth_date_is_rejected(
        self,
        birth_date: str,
    ):
        payload = self._valid_payload()
        payload["birth_date"] = birth_date

        status, _ = RequestGenerator.POST_client(payload)

        assert status in (400, 422)

    @pytest.mark.parametrize(
        "missing_field",
        [
            "name",
            "document_number",
            "birth_date",
        ],
    )
    def test_required_fields_are_required(
        self,
        missing_field: str,
    ):
        payload = self._valid_payload()
        del payload[missing_field]

        status, _ = RequestGenerator.POST_client(payload)

        assert status == 400

    def test_empty_name_is_rejected(self):
        payload = self._valid_payload()
        payload["name"] = ""

        status, _ = RequestGenerator.POST_client(payload)

        assert status == 400

    def test_name_longer_than_255_characters_is_rejected(self):
        payload = self._valid_payload()
        payload["name"] = "A" * 256

        status, _ = RequestGenerator.POST_client(payload)

        assert status == 400

    def test_additional_property_is_rejected(self):
        payload = self._valid_payload()
        payload["email"] = "teste@example.com"

        status, _ = RequestGenerator.POST_client(payload)

        assert status == 400