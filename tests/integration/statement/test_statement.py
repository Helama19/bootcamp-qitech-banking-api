from uuid import uuid4

import pytest

from tests.utils import RandomGenerator, RequestGenerator


class TestStatement:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_account(name: str) -> str:
        client_payload = {
            "name": name,
            "document_number": TestStatement._cpf_without_mask(),
            "birth_date": "2000-01-01",
        }

        status, client_response = RequestGenerator.POST_client(
            client_payload
        )
        assert status == 201

        account_payload = {
            "client_key": client_response["client_key"],
        }

        status, account_response = RequestGenerator.POST_account(
            account_payload
        )
        assert status == 201

        return account_response["account_key"]

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
    ) -> dict:
        payload = {
            "source_account_key": source_account_key,
            "destination_account_key": destination_account_key,
            "amount": amount,
            "idempotency_key": str(uuid4()),
        }

        status, response = RequestGenerator.POST_transfer(payload)

        assert status == 201
        return response

    def test_empty_account_has_empty_statement(self):
        account_key = self._create_account(
            "Cliente Extrato Vazio"
        )

        status, response = RequestGenerator.GET_statement(
            account_key,
            page=1,
            page_size=20,
        )

        assert status == 200
        assert response["account_key"] == account_key
        assert response["page"] == 1
        assert response["page_size"] == 20
        assert response["total"] == 0
        assert response["transactions"] == []

    def test_deposit_appears_as_incoming_transaction(self):
        account_key = self._create_account(
            "Cliente Extrato Deposito"
        )

        deposit_response = self._deposit(
            account_key,
            "100.00",
        )

        status, response = RequestGenerator.GET_statement(
            account_key,
            page=1,
            page_size=20,
        )

        assert status == 200
        assert response["total"] == 1
        assert len(response["transactions"]) == 1

        transaction = response["transactions"][0]

        assert (
            transaction["transaction_key"]
            == deposit_response["transaction_key"]
        )
        assert transaction["type"] == "deposit"
        assert transaction["direction"] == "IN"
        assert transaction["amount"] == "100.00"
        assert transaction["fee"] == "0.00"
        assert transaction["total_amount"] == "100.00"
        assert "created_at" in transaction

    def test_outgoing_transfer_shows_fee(self):
        source_account_key = self._create_account(
            "Origem Extrato Saida"
        )
        destination_account_key = self._create_account(
            "Destino Extrato Saida"
        )

        self._deposit(source_account_key, "100.00")

        transfer_response = self._transfer(
            source_account_key,
            destination_account_key,
            "25.00",
        )

        status, statement = RequestGenerator.GET_statement(
            source_account_key,
            page=1,
            page_size=20,
        )

        assert status == 200

        transaction = statement["transactions"][0]

        assert (
            transaction["transaction_key"]
            == transfer_response["transaction_key"]
        )
        assert transaction["type"] == "transfer"
        assert transaction["direction"] == "OUT"
        assert transaction["amount"] == "25.00"
        assert transaction["fee"] == "0.25"
        assert transaction["total_amount"] == "25.25"

    def test_incoming_transfer_does_not_show_fee_for_receiver(self):
        source_account_key = self._create_account(
            "Origem Extrato Entrada"
        )
        destination_account_key = self._create_account(
            "Destino Extrato Entrada"
        )

        self._deposit(source_account_key, "100.00")

        transfer_response = self._transfer(
            source_account_key,
            destination_account_key,
            "25.00",
        )

        status, statement = RequestGenerator.GET_statement(
            destination_account_key,
            page=1,
            page_size=20,
        )

        assert status == 200
        assert statement["total"] == 1

        transaction = statement["transactions"][0]

        assert (
            transaction["transaction_key"]
            == transfer_response["transaction_key"]
        )
        assert transaction["type"] == "transfer"
        assert transaction["direction"] == "IN"
        assert transaction["amount"] == "25.00"
        assert transaction["fee"] == "0.00"
        assert transaction["total_amount"] == "25.00"

    def test_statement_is_ordered_from_newest_to_oldest(self):
        account_key = self._create_account(
            "Cliente Ordem Extrato"
        )

        first = self._deposit(account_key, "10.00")
        second = self._deposit(account_key, "20.00")
        third = self._deposit(account_key, "30.00")

        status, response = RequestGenerator.GET_statement(
            account_key,
            page=1,
            page_size=20,
        )

        assert status == 200
        assert response["total"] == 3

        transactions = response["transactions"]

        assert len(transactions) == 3

        assert (
            transactions[0]["transaction_key"]
            == third["transaction_key"]
        )
        assert (
            transactions[1]["transaction_key"]
            == second["transaction_key"]
        )
        assert (
            transactions[2]["transaction_key"]
            == first["transaction_key"]
        )

    def test_statement_pagination_returns_correct_pages(self):
        account_key = self._create_account(
            "Cliente Paginacao Extrato"
        )

        first = self._deposit(account_key, "10.00")
        second = self._deposit(account_key, "20.00")
        third = self._deposit(account_key, "30.00")
        fourth = self._deposit(account_key, "40.00")
        fifth = self._deposit(account_key, "50.00")

        status, page_one = RequestGenerator.GET_statement(
            account_key,
            page=1,
            page_size=2,
        )

        assert status == 200
        assert page_one["page"] == 1
        assert page_one["page_size"] == 2
        assert page_one["total"] == 5
        assert len(page_one["transactions"]) == 2

        assert (
            page_one["transactions"][0]["transaction_key"]
            == fifth["transaction_key"]
        )
        assert (
            page_one["transactions"][1]["transaction_key"]
            == fourth["transaction_key"]
        )

        status, page_two = RequestGenerator.GET_statement(
            account_key,
            page=2,
            page_size=2,
        )

        assert status == 200
        assert page_two["page"] == 2
        assert page_two["page_size"] == 2
        assert page_two["total"] == 5
        assert len(page_two["transactions"]) == 2

        assert (
            page_two["transactions"][0]["transaction_key"]
            == third["transaction_key"]
        )
        assert (
            page_two["transactions"][1]["transaction_key"]
            == second["transaction_key"]
        )

        status, page_three = RequestGenerator.GET_statement(
            account_key,
            page=3,
            page_size=2,
        )

        assert status == 200
        assert page_three["page"] == 3
        assert page_three["page_size"] == 2
        assert page_three["total"] == 5
        assert len(page_three["transactions"]) == 1

        assert (
            page_three["transactions"][0]["transaction_key"]
            == first["transaction_key"]
        )

    def test_page_after_last_page_is_empty(self):
        account_key = self._create_account(
            "Cliente Pagina Vazia"
        )

        self._deposit(account_key, "10.00")
        self._deposit(account_key, "20.00")

        status, response = RequestGenerator.GET_statement(
            account_key,
            page=10,
            page_size=2,
        )

        assert status == 200
        assert response["page"] == 10
        assert response["page_size"] == 2
        assert response["total"] == 2
        assert response["transactions"] == []

    def test_statement_contains_deposits_incoming_and_outgoing_transfers(
        self,
    ):
        main_account_key = self._create_account(
            "Conta Extrato Misto"
        )
        other_account_key = self._create_account(
            "Outra Conta Extrato Misto"
        )

        deposit = self._deposit(
            main_account_key,
            "100.00",
        )

        outgoing = self._transfer(
            main_account_key,
            other_account_key,
            "20.00",
        )

        self._deposit(
            other_account_key,
            "50.00",
        )

        incoming = self._transfer(
            other_account_key,
            main_account_key,
            "10.00",
        )

        status, response = RequestGenerator.GET_statement(
            main_account_key,
            page=1,
            page_size=20,
        )

        assert status == 200
        assert response["total"] == 3

        transactions = response["transactions"]

        assert (
            transactions[0]["transaction_key"]
            == incoming["transaction_key"]
        )
        assert transactions[0]["direction"] == "IN"
        assert transactions[0]["type"] == "transfer"

        assert (
            transactions[1]["transaction_key"]
            == outgoing["transaction_key"]
        )
        assert transactions[1]["direction"] == "OUT"
        assert transactions[1]["type"] == "transfer"

        assert (
            transactions[2]["transaction_key"]
            == deposit["transaction_key"]
        )
        assert transactions[2]["direction"] == "IN"
        assert transactions[2]["type"] == "deposit"

    def test_nonexistent_account_statement_is_rejected(self):
        status, response = RequestGenerator.GET_statement(
            str(uuid4()),
            page=1,
            page_size=20,
        )

        assert status == 404
        assert "code" in response

    @pytest.mark.parametrize(
        ("page", "page_size"),
        [
            (0, 20),
            (-1, 20),
            (1, 0),
            (1, -1),
            (1, 101),
        ],
    )
    def test_invalid_pagination_is_rejected(
        self,
        page: int,
        page_size: int,
    ):
        account_key = self._create_account(
            "Cliente Paginacao Invalida"
        )

        status, _ = RequestGenerator.GET_statement(
            account_key,
            page=page,
            page_size=page_size,
        )

        assert status == 400