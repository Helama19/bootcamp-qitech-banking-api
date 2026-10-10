from uuid import uuid4

import pytest

from tests.utils import RandomGenerator, RequestGenerator


class TestDeposit:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_client(name: str = "Cliente Deposito") -> str:
        payload = {
            "name": name,
            "document_number": TestDeposit._cpf_without_mask(),
            "birth_date": "2000-01-01",
        }

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        return response["client_key"]

    @staticmethod
    def _create_account(name: str = "Cliente Deposito") -> str:
        client_key = TestDeposit._create_client(name)

        status, response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

        assert status == 201
        return response["account_key"]

    @staticmethod
    def _deposit(
        account_key: str,
        amount: str,
        idempotency_key: str | None = None,
    ):
        if idempotency_key is None:
            idempotency_key = str(uuid4())

        payload = {
            "account_key": account_key,
            "amount": amount,
            "idempotency_key": idempotency_key,
        }

        return RequestGenerator.POST_deposit(payload)

    def test_deposit_adds_money_to_account(self):
        account_key = self._create_account()

        status, response = self._deposit(
            account_key,
            "100.00",
        )

        assert status == 201
        assert response["account_key"] == account_key
        assert response["type"] == "deposit"
        assert response["amount"] == "100.00"
        assert response["balance"] == "100.00"
        assert "transaction_key" in response

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "100.00"

    def test_multiple_deposits_accumulate_balance(self):
        account_key = self._create_account(
            "Cliente Multiplos Depositos"
        )

        first_status, first_response = self._deposit(
            account_key,
            "40.00",
        )

        second_status, second_response = self._deposit(
            account_key,
            "60.00",
        )

        assert first_status == 201
        assert first_response["balance"] == "40.00"

        assert second_status == 201
        assert second_response["balance"] == "100.00"

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "100.00"

    def test_repeated_deposit_is_idempotent(self):
        account_key = self._create_account(
            "Cliente Deposito Idempotente"
        )

        idempotency_key = str(uuid4())

        first_status, first_response = self._deposit(
            account_key,
            "50.00",
            idempotency_key,
        )

        second_status, second_response = self._deposit(
            account_key,
            "50.00",
            idempotency_key,
        )

        assert first_status == 201
        assert second_status == 201

        assert (
            first_response["transaction_key"]
            == second_response["transaction_key"]
        )

        assert first_response["amount"] == "50.00"
        assert second_response["amount"] == "50.00"

        assert second_response["balance"] == "50.00"

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "50.00"

    def test_same_idempotency_key_with_different_amount_is_rejected(self):
        account_key = self._create_account(
            "Cliente Conflito Valor"
        )

        idempotency_key = str(uuid4())

        first_status, _ = self._deposit(
            account_key,
            "50.00",
            idempotency_key,
        )

        second_status, second_response = self._deposit(
            account_key,
            "60.00",
            idempotency_key,
        )

        assert first_status == 201
        assert second_status == 409
        assert "code" in second_response

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "50.00"

    def test_same_idempotency_key_for_different_account_is_rejected(self):
        first_account_key = self._create_account(
            "Primeira Conta Idempotencia"
        )
        second_account_key = self._create_account(
            "Segunda Conta Idempotencia"
        )

        idempotency_key = str(uuid4())

        first_status, _ = self._deposit(
            first_account_key,
            "25.00",
            idempotency_key,
        )

        second_status, second_response = self._deposit(
            second_account_key,
            "25.00",
            idempotency_key,
        )

        assert first_status == 201
        assert second_status == 409
        assert "code" in second_response

        first_balance_status, first_balance = (
            RequestGenerator.GET_balance(first_account_key)
        )
        second_balance_status, second_balance = (
            RequestGenerator.GET_balance(second_account_key)
        )

        assert first_balance_status == 200
        assert second_balance_status == 200

        assert first_balance["balance"] == "25.00"
        assert second_balance["balance"] == "0.00"

    def test_zero_deposit_is_rejected(self):
        account_key = self._create_account(
            "Cliente Deposito Zero"
        )

        status, response = self._deposit(
            account_key,
            "0.00",
        )

        assert status == 422
        assert "code" in response

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "0.00"

    def test_deposit_to_nonexistent_account_is_rejected(self):
        status, response = self._deposit(
            str(uuid4()),
            "10.00",
        )

        assert status == 404
        assert "code" in response

    def test_blocked_account_can_receive_deposit(self):
        account_key = self._create_account(
            "Cliente Bloqueado Deposito"
        )

        status, response = RequestGenerator.PATCH_account_status(
            account_key,
            {"status": "blocked"},
        )

        assert status == 200
        assert response["status"] == "blocked"

        deposit_status, deposit_response = self._deposit(
            account_key,
            "30.00",
        )

        assert deposit_status == 201
        assert deposit_response["balance"] == "30.00"

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "30.00"

    def test_closed_account_cannot_receive_deposit(self):
        account_key = self._create_account(
            "Cliente Fechado Deposito"
        )

        status, response = RequestGenerator.PATCH_account_status(
            account_key,
            {"status": "closed"},
        )

        assert status == 200
        assert response["status"] == "closed"

        deposit_status, deposit_response = self._deposit(
            account_key,
            "30.00",
        )

        assert deposit_status == 422
        assert "code" in deposit_response

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200
        assert balance_response["balance"] == "0.00"

    @pytest.mark.parametrize(
        "amount",
        [
            "-1.00",
            "-100.00",
            "10",
            "10.0",
            "10.000",
            ".50",
            "1,00",
            "abc",
            "",
        ],
    )
    def test_invalid_amount_format_is_rejected(
        self,
        amount: str,
    ):
        account_key = self._create_account(
            "Cliente Formato Valor"
        )

        status, _ = self._deposit(
            account_key,
            amount,
        )

        assert status == 400

    @pytest.mark.parametrize(
        "missing_field",
        [
            "account_key",
            "amount",
            "idempotency_key",
        ],
    )
    def test_required_fields_are_required(
        self,
        missing_field: str,
    ):
        payload = {
            "account_key": str(uuid4()),
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
        }

        del payload[missing_field]

        status, _ = RequestGenerator.POST_deposit(payload)

        assert status == 400

    def test_additional_property_is_rejected(self):
        account_key = self._create_account(
            "Cliente Campo Extra Deposito"
        )

        payload = {
            "account_key": account_key,
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
            "description": "Dinheiro gratis",
        }

        status, _ = RequestGenerator.POST_deposit(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "account_key",
        [
            "",
            "abc",
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_invalid_account_key_format_is_rejected(
        self,
        account_key: str,
    ):
        payload = {
            "account_key": account_key,
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
        }

        status, _ = RequestGenerator.POST_deposit(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "idempotency_key",
        [
            "",
            "abc",
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_invalid_idempotency_key_format_is_rejected(
        self,
        idempotency_key: str,
    ):
        account_key = self._create_account(
            "Cliente Chave Invalida"
        )

        payload = {
            "account_key": account_key,
            "amount": "10.00",
            "idempotency_key": idempotency_key,
        }

        status, _ = RequestGenerator.POST_deposit(payload)

        assert status == 400