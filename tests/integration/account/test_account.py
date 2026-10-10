from uuid import uuid4

import pytest

from tests.utils import RandomGenerator, RequestGenerator


class TestAccount:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_client(name: str = "Cliente Conta") -> str:
        payload = {
            "name": name,
            "document_number": TestAccount._cpf_without_mask(),
            "birth_date": "2000-01-01",
        }

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        assert "client_key" in response

        return response["client_key"]

    def test_create_account_for_existing_client(self):
        client_key = self._create_client()

        payload = {
            "client_key": client_key,
        }

        status, response = RequestGenerator.POST_account(payload)

        assert status == 201
        assert "account_key" in response
        assert response["balance"] == "0.00"
        assert response["status"] == "active"

    def test_new_account_has_zero_balance(self):
        client_key = self._create_client("Cliente Saldo Inicial")

        status, response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

        assert status == 201
        assert response["balance"] == "0.00"

        account_key = response["account_key"]

        balance_status, balance_response = RequestGenerator.GET_balance(
            account_key
        )

        assert balance_status == 200
        assert balance_response["balance"] == "0.00"

    def test_new_account_is_active(self):
        client_key = self._create_client("Cliente Status Inicial")

        status, response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

        assert status == 201
        assert response["status"] == "active"

    def test_client_cannot_have_two_accounts(self):
        client_key = self._create_client("Cliente Duas Contas")

        first_status, first_response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

        second_status, second_response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

        assert first_status == 201
        assert "account_key" in first_response

        assert second_status == 409
        assert "code" in second_response

    def test_account_for_nonexistent_client_is_rejected(self):
        payload = {
            "client_key": str(uuid4()),
        }

        status, response = RequestGenerator.POST_account(payload)

        assert status == 404
        assert "code" in response

    def test_missing_client_key_is_rejected(self):
        payload = {}

        status, _ = RequestGenerator.POST_account(payload)

        assert status == 400

    def test_additional_property_is_rejected(self):
        client_key = self._create_client("Cliente Campo Extra")

        payload = {
            "client_key": client_key,
            "balance": "1000000.00",
        }

        status, _ = RequestGenerator.POST_account(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "client_key",
        [
            "",
            "abc",
            "123456",
            "00000000-0000-0000-0000-000000000000",
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",
            "550e8400-e29b-41d4-a716-446655440000-extra",
        ],
    )
    def test_invalid_client_key_format_is_rejected(
        self,
        client_key: str,
    ):
        payload = {
            "client_key": client_key,
        }

        status, _ = RequestGenerator.POST_account(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "client_key",
        [
            None,
            123,
            True,
            [],
            {},
        ],
    )
    def test_invalid_client_key_type_is_rejected(
        self,
        client_key,
    ):
        payload = {
            "client_key": client_key,
        }

        status, _ = RequestGenerator.POST_account(payload)

        assert status == 400