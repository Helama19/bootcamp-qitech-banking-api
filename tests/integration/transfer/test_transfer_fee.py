from uuid import uuid4

from tests.utils import RandomGenerator, RequestGenerator


class TestTransferFee:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_client(name: str) -> str:
        payload = {
            "name": name,
            "document_number": TestTransferFee._cpf_without_mask(),
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

    def test_transfer_charges_one_percent_fee(self):
        source_client_key = self._create_client(
            "Cliente Origem"
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

        transfer_payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": "50.00",
            "idempotency_key": str(uuid4()),
        }

        status, response = RequestGenerator.POST_transfer(
            transfer_payload
        )

        assert status == 201
        assert response["amount"] == "50.00"
        assert response["fee"] == "0.50"
        assert response["total_amount"] == "50.50"
        assert response["source_balance"] == "49.50"
        assert response["destination_balance"] == "50.00"

    def test_repeated_transfer_is_idempotent(self):
        source_client_key = self._create_client(
            "Origem Idempotencia"
        )
        destination_client_key = self._create_client(
            "Destino Idempotencia"
        )

        source_account_key = self._create_account(
            source_client_key
        )
        destination_account_key = self._create_account(
            destination_client_key
        )

        self._deposit(source_account_key, "100.00")

        transfer_payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": "50.00",
            "idempotency_key": str(uuid4()),
        }

        first_status, first_response = (
            RequestGenerator.POST_transfer(
                transfer_payload
            )
        )

        second_status, second_response = (
            RequestGenerator.POST_transfer(
                transfer_payload
            )
        )

        assert first_status == 201
        assert second_status == 201

        assert (
            first_response["transaction_key"]
            == second_response["transaction_key"]
        )

        assert second_response["amount"] == "50.00"
        assert second_response["fee"] == "0.50"
        assert second_response["total_amount"] == "50.50"
        assert second_response["source_balance"] == "49.50"
        assert second_response["destination_balance"] == "50.00"

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )

        assert status == 200
        assert source_balance["balance"] == "49.50"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )

        assert status == 200
        assert destination_balance["balance"] == "50.00"

    def test_transfer_refuses_balance_without_money_for_fee(self):
        source_client_key = self._create_client(
            "Origem Saldo Insuficiente"
        )
        destination_client_key = self._create_client(
            "Destino Saldo Insuficiente"
        )

        source_account_key = self._create_account(
            source_client_key
        )
        destination_account_key = self._create_account(
            destination_client_key
        )

        self._deposit(source_account_key, "50.50")

        transfer_payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": "50.50",
            "idempotency_key": str(uuid4()),
        }

        status, response = RequestGenerator.POST_transfer(
            transfer_payload
        )

        assert status == 422
        assert response["code"] == "QIT002009"

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )

        assert status == 200
        assert source_balance["balance"] == "50.50"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )

        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_statement_shows_fee_direction_and_pagination(self):
        source_client_key = self._create_client(
            "Origem Extrato"
        )
        destination_client_key = self._create_client(
            "Destino Extrato"
        )

        source_account_key = self._create_account(
            source_client_key
        )
        destination_account_key = self._create_account(
            destination_client_key
        )

        self._deposit(source_account_key, "100.00")

        transfer_payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": "20.00",
            "idempotency_key": str(uuid4()),
        }

        status, transfer_response = (
            RequestGenerator.POST_transfer(
                transfer_payload
            )
        )

        assert status == 201

        status, source_statement = (
            RequestGenerator.GET_statement(
                source_account_key,
                page=1,
                page_size=1,
            )
        )

        assert status == 200
        assert source_statement["page"] == 1
        assert source_statement["page_size"] == 1
        assert source_statement["total"] == 2
        assert len(source_statement["transactions"]) == 1

        source_transaction = (
            source_statement["transactions"][0]
        )

        assert (
            source_transaction["transaction_key"]
            == transfer_response["transaction_key"]
        )
        assert source_transaction["type"] == "transfer"
        assert source_transaction["direction"] == "OUT"
        assert source_transaction["amount"] == "20.00"
        assert source_transaction["fee"] == "0.20"
        assert source_transaction["total_amount"] == "20.20"

        status, destination_statement = (
            RequestGenerator.GET_statement(
                destination_account_key,
                page=1,
                page_size=20,
            )
        )

        assert status == 200
        assert destination_statement["total"] == 1

        destination_transaction = (
            destination_statement["transactions"][0]
        )

        assert (
            destination_transaction["transaction_key"]
            == transfer_response["transaction_key"]
        )
        assert destination_transaction["type"] == "transfer"
        assert destination_transaction["direction"] == "IN"
        assert destination_transaction["amount"] == "20.00"
        assert destination_transaction["fee"] == "0.00"
        assert destination_transaction["total_amount"] == "20.00"