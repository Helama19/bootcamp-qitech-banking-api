from uuid import uuid4

from tests.utils import RandomGenerator, RequestGenerator


class TestAccountStatus:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_client(name: str) -> str:
        payload = {
            "name": name,
            "document_number": TestAccountStatus._cpf_without_mask(),
            "birth_date": "2000-01-01",
        }

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201

        return response["client_key"]

    @staticmethod
    def _create_account(client_key: str) -> str:
        payload = {
            "client_key": client_key,
        }

        status, response = RequestGenerator.POST_account(payload)

        assert status == 201

        return response["account_key"]

    @staticmethod
    def _deposit(account_key: str, amount: str) -> dict:
        payload = {
            "account_key": account_key,
            "amount": amount,
            "idempotency_key": str(uuid4()),
        }

        status, response = RequestGenerator.POST_deposit(payload)

        assert status == 201

        return response

    @staticmethod
    def _change_status(account_key: str, new_status: str):
        payload = {
            "status": new_status,
        }

        return RequestGenerator.PATCH_account_status(
            account_key,
            payload,
        )

    def test_blocked_account_can_receive_but_cannot_send(self):
        source_client_key = self._create_client(
            "Cliente Bloqueado"
        )
        destination_client_key = self._create_client(
            "Cliente Destino"
        )

        source_account_key = self._create_account(
            source_client_key
        )
        destination_account_key = self._create_account(
            destination_client_key
        )

        self._deposit(source_account_key, "100.00")

        status, response = self._change_status(
            source_account_key,
            "blocked",
        )

        assert status == 200
        assert response["status"] == "blocked"
        assert response["balance"] == "100.00"

        self._deposit(source_account_key, "20.00")

        status, balance_response = RequestGenerator.GET_balance(
            source_account_key
        )

        assert status == 200
        assert balance_response["balance"] == "120.00"

        transfer_payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": "50.00",
            "idempotency_key": str(uuid4()),
        }

        status, _ = RequestGenerator.POST_transfer(
            transfer_payload
        )

        assert status == 422

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )

        assert status == 200
        assert source_balance["balance"] == "120.00"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )

        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_account_cannot_close_with_nonzero_balance(self):
        client_key = self._create_client(
            "Cliente Com Saldo"
        )

        account_key = self._create_account(client_key)

        self._deposit(account_key, "10.00")

        status, _ = self._change_status(
            account_key,
            "closed",
        )

        assert status == 422

        status, balance_response = RequestGenerator.GET_balance(
            account_key
        )

        assert status == 200
        assert balance_response["balance"] == "10.00"

    def test_closed_account_is_final_and_cannot_receive_deposit(self):
        client_key = self._create_client(
            "Cliente Encerrado"
        )

        account_key = self._create_account(client_key)

        status, response = self._change_status(
            account_key,
            "closed",
        )

        assert status == 200
        assert response["status"] == "closed"
        assert response["balance"] == "0.00"

        deposit_payload = {
            "account_key": account_key,
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
        }

        status, _ = RequestGenerator.POST_deposit(
            deposit_payload
        )

        assert status == 422

        status, _ = self._change_status(
            account_key,
            "active",
        )

        assert status == 422

        status, balance_response = RequestGenerator.GET_balance(
            account_key
        )

        assert status == 200
        assert balance_response["balance"] == "0.00"

    def test_repeating_same_status_is_idempotent(self):
        client_key = self._create_client(
            "Cliente Status Idempotente"
        )

        account_key = self._create_account(client_key)

        first_status, first_response = self._change_status(
            account_key,
            "blocked",
        )

        second_status, second_response = self._change_status(
            account_key,
            "blocked",
        )

        assert first_status == 200
        assert second_status == 200

        assert first_response["account_key"] == account_key
        assert second_response["account_key"] == account_key

        assert first_response["status"] == "blocked"
        assert second_response["status"] == "blocked"

        assert first_response["balance"] == "0.00"
        assert second_response["balance"] == "0.00"