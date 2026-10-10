from uuid import uuid4

import pytest

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
    def _create_account(name: str) -> str:
        client_key = TestTransferFee._create_client(name)

        status, response = RequestGenerator.POST_account(
            {"client_key": client_key}
        )

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
    def _transfer(
        source_account_key: str,
        destination_account_key: str,
        amount: str,
        idempotency_key: str | None = None,
    ):
        if idempotency_key is None:
            idempotency_key = str(uuid4())

        payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": amount,
            "idempotency_key": idempotency_key,
        }

        return RequestGenerator.POST_transfer(payload)

    def test_transfer_charges_one_percent_fee(self):
        source_account_key = self._create_account("Cliente Origem")
        destination_account_key = self._create_account("Cliente Destino")

        self._deposit(source_account_key, "100.00")

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "50.00",
        )

        assert status == 201
        assert response["type"] == "transfer"
        assert response["amount"] == "50.00"
        assert response["fee"] == "0.50"
        assert response["total_amount"] == "50.50"
        assert response["source_balance"] == "49.50"
        assert response["destination_balance"] == "50.00"
        assert "transaction_key" in response

    def test_repeated_transfer_is_idempotent(self):
        source_account_key = self._create_account(
            "Origem Idempotencia"
        )
        destination_account_key = self._create_account(
            "Destino Idempotencia"
        )

        self._deposit(source_account_key, "100.00")

        idempotency_key = str(uuid4())

        first_status, first_response = self._transfer(
            source_account_key,
            destination_account_key,
            "50.00",
            idempotency_key,
        )

        second_status, second_response = self._transfer(
            source_account_key,
            destination_account_key,
            "50.00",
            idempotency_key,
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
        source_account_key = self._create_account(
            "Origem Saldo Insuficiente"
        )
        destination_account_key = self._create_account(
            "Destino Saldo Insuficiente"
        )

        self._deposit(source_account_key, "50.50")

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "50.50",
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
        source_account_key = self._create_account("Origem Extrato")
        destination_account_key = self._create_account("Destino Extrato")

        self._deposit(source_account_key, "100.00")

        status, transfer_response = self._transfer(
            source_account_key,
            destination_account_key,
            "20.00",
        )

        assert status == 201

        status, source_statement = RequestGenerator.GET_statement(
            source_account_key,
            page=1,
            page_size=1,
        )

        assert status == 200
        assert source_statement["page"] == 1
        assert source_statement["page_size"] == 1
        assert source_statement["total"] == 2
        assert len(source_statement["transactions"]) == 1

        source_transaction = source_statement["transactions"][0]

        assert (
            source_transaction["transaction_key"]
            == transfer_response["transaction_key"]
        )
        assert source_transaction["type"] == "transfer"
        assert source_transaction["direction"] == "OUT"
        assert source_transaction["amount"] == "20.00"
        assert source_transaction["fee"] == "0.20"
        assert source_transaction["total_amount"] == "20.20"

        status, destination_statement = RequestGenerator.GET_statement(
            destination_account_key,
            page=1,
            page_size=20,
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

    def test_transfer_with_exact_balance_including_fee_succeeds(self):
        source_account_key = self._create_account(
            "Origem Saldo Exato"
        )
        destination_account_key = self._create_account(
            "Destino Saldo Exato"
        )

        self._deposit(source_account_key, "50.50")

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "50.00",
        )

        assert status == 201
        assert response["amount"] == "50.00"
        assert response["fee"] == "0.50"
        assert response["total_amount"] == "50.50"
        assert response["source_balance"] == "0.00"
        assert response["destination_balance"] == "50.00"

    def test_transfer_fee_rounds_half_up(self):
        source_account_key = self._create_account(
            "Origem Arredondamento"
        )
        destination_account_key = self._create_account(
            "Destino Arredondamento"
        )

        self._deposit(source_account_key, "10.00")

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "1.50",
        )

        assert status == 201
        assert response["amount"] == "1.50"

        # 1% de 1.50 = 0.015.
        # ROUND_HALF_UP deve produzir 0.02.
        assert response["fee"] == "0.02"
        assert response["total_amount"] == "1.52"
        assert response["source_balance"] == "8.48"
        assert response["destination_balance"] == "1.50"

    def test_transfer_to_same_account_is_rejected(self):
        account_key = self._create_account(
            "Cliente Mesma Conta"
        )

        self._deposit(account_key, "100.00")

        status, response = self._transfer(
            account_key,
            account_key,
            "10.00",
        )

        assert status == 422
        assert "code" in response

        status, balance_response = RequestGenerator.GET_balance(
            account_key
        )

        assert status == 200
        assert balance_response["balance"] == "100.00"

    def test_nonexistent_source_account_is_rejected(self):
        destination_account_key = self._create_account(
            "Destino Origem Inexistente"
        )

        status, response = self._transfer(
            str(uuid4()),
            destination_account_key,
            "10.00",
        )

        assert status == 404
        assert "code" in response

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )

        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_nonexistent_destination_account_is_rejected(self):
        source_account_key = self._create_account(
            "Origem Destino Inexistente"
        )

        self._deposit(source_account_key, "100.00")

        status, response = self._transfer(
            source_account_key,
            str(uuid4()),
            "10.00",
        )

        assert status == 404
        assert "code" in response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )

        assert status == 200
        assert source_balance["balance"] == "100.00"

    def test_blocked_source_account_cannot_send(self):
        source_account_key = self._create_account(
            "Origem Bloqueada"
        )
        destination_account_key = self._create_account(
            "Destino Origem Bloqueada"
        )

        self._deposit(source_account_key, "100.00")

        status, response = RequestGenerator.PATCH_account_status(
            source_account_key,
            {"status": "blocked"},
        )

        assert status == 200
        assert response["status"] == "blocked"

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "20.00",
        )

        assert status == 422
        assert "code" in response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "100.00"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )
        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_blocked_destination_account_can_receive(self):
        source_account_key = self._create_account(
            "Origem Destino Bloqueado"
        )
        destination_account_key = self._create_account(
            "Destino Bloqueado"
        )

        self._deposit(source_account_key, "100.00")

        status, response = RequestGenerator.PATCH_account_status(
            destination_account_key,
            {"status": "blocked"},
        )

        assert status == 200
        assert response["status"] == "blocked"

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "20.00",
        )

        assert status == 201
        assert response["fee"] == "0.20"
        assert response["source_balance"] == "79.80"
        assert response["destination_balance"] == "20.00"

    def test_closed_destination_account_cannot_receive(self):
        source_account_key = self._create_account(
            "Origem Destino Fechado"
        )
        destination_account_key = self._create_account(
            "Destino Fechado"
        )

        self._deposit(source_account_key, "100.00")

        status, response = RequestGenerator.PATCH_account_status(
            destination_account_key,
            {"status": "closed"},
        )

        assert status == 200
        assert response["status"] == "closed"

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "20.00",
        )

        assert status == 422
        assert "code" in response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "100.00"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )
        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_same_idempotency_key_with_different_amount_is_rejected(self):
        source_account_key = self._create_account(
            "Origem Conflito Valor"
        )
        destination_account_key = self._create_account(
            "Destino Conflito Valor"
        )

        self._deposit(source_account_key, "100.00")

        idempotency_key = str(uuid4())

        first_status, _ = self._transfer(
            source_account_key,
            destination_account_key,
            "20.00",
            idempotency_key,
        )

        second_status, second_response = self._transfer(
            source_account_key,
            destination_account_key,
            "30.00",
            idempotency_key,
        )

        assert first_status == 201
        assert second_status == 409
        assert "code" in second_response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "79.80"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )
        assert status == 200
        assert destination_balance["balance"] == "20.00"

    def test_same_idempotency_key_with_different_destination_is_rejected(
        self,
    ):
        source_account_key = self._create_account(
            "Origem Conflito Destino"
        )
        first_destination_key = self._create_account(
            "Primeiro Destino"
        )
        second_destination_key = self._create_account(
            "Segundo Destino"
        )

        self._deposit(source_account_key, "100.00")

        idempotency_key = str(uuid4())

        first_status, _ = self._transfer(
            source_account_key,
            first_destination_key,
            "20.00",
            idempotency_key,
        )

        second_status, second_response = self._transfer(
            source_account_key,
            second_destination_key,
            "20.00",
            idempotency_key,
        )

        assert first_status == 201
        assert second_status == 409
        assert "code" in second_response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "79.80"

        status, first_destination_balance = (
            RequestGenerator.GET_balance(first_destination_key)
        )
        assert status == 200
        assert first_destination_balance["balance"] == "20.00"

        status, second_destination_balance = (
            RequestGenerator.GET_balance(second_destination_key)
        )
        assert status == 200
        assert second_destination_balance["balance"] == "0.00"

    def test_deposit_idempotency_key_cannot_be_reused_for_transfer(self):
        source_account_key = self._create_account(
            "Origem Chave Deposito"
        )
        destination_account_key = self._create_account(
            "Destino Chave Deposito"
        )

        idempotency_key = str(uuid4())

        deposit_payload = {
            "account_key": source_account_key,
            "amount": "50.00",
            "idempotency_key": idempotency_key,
        }

        deposit_status, _ = RequestGenerator.POST_deposit(
            deposit_payload
        )

        assert deposit_status == 201

        transfer_status, transfer_response = self._transfer(
            source_account_key,
            destination_account_key,
            "10.00",
            idempotency_key,
        )

        assert transfer_status == 409
        assert "code" in transfer_response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "50.00"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )
        assert status == 200
        assert destination_balance["balance"] == "0.00"

    def test_zero_transfer_is_rejected(self):
        source_account_key = self._create_account(
            "Origem Transferencia Zero"
        )
        destination_account_key = self._create_account(
            "Destino Transferencia Zero"
        )

        self._deposit(source_account_key, "100.00")

        status, response = self._transfer(
            source_account_key,
            destination_account_key,
            "0.00",
        )

        assert status == 422
        assert "code" in response

        status, source_balance = RequestGenerator.GET_balance(
            source_account_key
        )
        assert status == 200
        assert source_balance["balance"] == "100.00"

        status, destination_balance = RequestGenerator.GET_balance(
            destination_account_key
        )
        assert status == 200
        assert destination_balance["balance"] == "0.00"

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
        payload = {
            "source_account_key": str(uuid4()),
            "destination_account_key": str(uuid4()),
            "amount": amount,
            "idempotency_key": str(uuid4()),
        }

        status, _ = RequestGenerator.POST_transfer(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "missing_field",
        [
            "source_account_key",
            "destination_account_key",
            "amount",
            "idempotency_key",
        ],
    )
    def test_required_fields_are_required(
        self,
        missing_field: str,
    ):
        payload = {
            "source_account_key": str(uuid4()),
            "destination_account_key": str(uuid4()),
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
        }

        del payload[missing_field]

        status, _ = RequestGenerator.POST_transfer(payload)

        assert status == 400

    def test_additional_property_is_rejected(self):
        payload = {
            "source_account_key": str(uuid4()),
            "destination_account_key": str(uuid4()),
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
            "description": "Campo nao permitido",
        }

        status, _ = RequestGenerator.POST_transfer(payload)

        assert status == 400

    @pytest.mark.parametrize(
        "field",
        [
            "source_account_key",
            "destination_account_key",
            "idempotency_key",
        ],
    )
    @pytest.mark.parametrize(
        "invalid_uuid",
        [
            "",
            "abc",
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_invalid_uuid_fields_are_rejected(
        self,
        field: str,
        invalid_uuid: str,
    ):
        payload = {
            "source_account_key": str(uuid4()),
            "destination_account_key": str(uuid4()),
            "amount": "10.00",
            "idempotency_key": str(uuid4()),
        }

        payload[field] = invalid_uuid

        status, _ = RequestGenerator.POST_transfer(payload)

        assert status == 400