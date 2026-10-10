from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.utils import RandomGenerator, RequestGenerator


class TestConcurrency:
    @staticmethod
    def _cpf_without_mask() -> str:
        cpf = RandomGenerator.generate_cpf()
        return cpf.replace(".", "").replace("-", "")

    @staticmethod
    def _create_account(name: str) -> str:
        client_payload = {
            "name": name,
            "document_number": TestConcurrency._cpf_without_mask(),
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

    def test_concurrent_transfers_cannot_spend_same_balance_twice(self):
        source_account_key = self._create_account(
            "Origem Concorrencia Saldo"
        )

        first_destination_key = self._create_account(
            "Destino Concorrencia Um"
        )

        second_destination_key = self._create_account(
            "Destino Concorrencia Dois"
        )

        deposit_status, _ = self._deposit(
            source_account_key,
            "100.00",
        )

        assert deposit_status == 201

        first_idempotency_key = str(uuid4())
        second_idempotency_key = str(uuid4())

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                self._transfer,
                source_account_key,
                first_destination_key,
                "60.00",
                first_idempotency_key,
            )

            second_future = executor.submit(
                self._transfer,
                source_account_key,
                second_destination_key,
                "60.00",
                second_idempotency_key,
            )

            first_result = first_future.result()
            second_result = second_future.result()

        results = [
            first_result,
            second_result,
        ]

        statuses = sorted(
            result[0]
            for result in results
        )

        # Só existe dinheiro suficiente para uma transferência.
        #
        # Cada transferência de R$ 60,00 custa:
        # R$ 60,00 + R$ 0,60 de tarifa = R$ 60,60.
        #
        # Portanto uma deve funcionar e a outra deve falhar.
        assert statuses == [201, 422]

        successful_results = [
            response
            for status, response in results
            if status == 201
        ]

        failed_results = [
            response
            for status, response in results
            if status == 422
        ]

        assert len(successful_results) == 1
        assert len(failed_results) == 1

        assert successful_results[0]["amount"] == "60.00"
        assert successful_results[0]["fee"] == "0.60"
        assert successful_results[0]["total_amount"] == "60.60"

        source_status, source_balance = (
            RequestGenerator.GET_balance(source_account_key)
        )

        first_status, first_balance = (
            RequestGenerator.GET_balance(first_destination_key)
        )

        second_status, second_balance = (
            RequestGenerator.GET_balance(second_destination_key)
        )

        assert source_status == 200
        assert first_status == 200
        assert second_status == 200

        # Apenas uma transferência pode ter debitado a origem.
        assert source_balance["balance"] == "39.40"

        destination_balances = sorted(
            [
                first_balance["balance"],
                second_balance["balance"],
            ]
        )

        # Não sabemos qual thread vai vencer.
        # Só sabemos que exatamente uma deve vencer.
        assert destination_balances == [
            "0.00",
            "60.00",
        ]

        statement_status, statement = (
            RequestGenerator.GET_statement(
                source_account_key,
                page=1,
                page_size=20,
            )
        )

        assert statement_status == 200

        # Um depósito + exatamente uma transferência.
        assert statement["total"] == 2

        transfers = [
            transaction
            for transaction in statement["transactions"]
            if transaction["type"] == "transfer"
        ]

        assert len(transfers) == 1

    def test_concurrent_same_transfer_idempotency_key_does_not_duplicate(self):
        source_account_key = self._create_account(
            "Origem Concorrencia Idempotencia"
        )

        destination_account_key = self._create_account(
            "Destino Concorrencia Idempotencia"
        )

        deposit_status, _ = self._deposit(
            source_account_key,
            "100.00",
        )

        assert deposit_status == 201

        idempotency_key = str(uuid4())

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                self._transfer,
                source_account_key,
                destination_account_key,
                "40.00",
                idempotency_key,
            )

            second_future = executor.submit(
                self._transfer,
                source_account_key,
                destination_account_key,
                "40.00",
                idempotency_key,
            )

            first_status, first_response = first_future.result()
            second_status, second_response = second_future.result()

        # As duas requisições representam a mesma operação.
        # Ambas podem receber a resposta de sucesso,
        # mas o dinheiro só pode ser movimentado uma vez.
        assert first_status == 201
        assert second_status == 201

        assert (
            first_response["transaction_key"]
            == second_response["transaction_key"]
        )

        source_status, source_balance = (
            RequestGenerator.GET_balance(source_account_key)
        )

        destination_status, destination_balance = (
            RequestGenerator.GET_balance(destination_account_key)
        )

        assert source_status == 200
        assert destination_status == 200

        # Transferência:
        # R$ 40,00 + R$ 0,40 de tarifa.
        #
        # Se a idempotência falhasse, o saldo seria alterado duas vezes.
        assert source_balance["balance"] == "59.60"
        assert destination_balance["balance"] == "40.00"

        statement_status, source_statement = (
            RequestGenerator.GET_statement(
                source_account_key,
                page=1,
                page_size=20,
            )
        )

        assert statement_status == 200

        # Um depósito + uma única transferência.
        assert source_statement["total"] == 2

        transfers = [
            transaction
            for transaction in source_statement["transactions"]
            if transaction["type"] == "transfer"
        ]

        assert len(transfers) == 1

        assert (
            transfers[0]["transaction_key"]
            == first_response["transaction_key"]
        )

    def test_concurrent_same_deposit_idempotency_key_does_not_duplicate(self):
        account_key = self._create_account(
            "Conta Concorrencia Deposito"
        )

        idempotency_key = str(uuid4())

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                self._deposit,
                account_key,
                "50.00",
                idempotency_key,
            )

            second_future = executor.submit(
                self._deposit,
                account_key,
                "50.00",
                idempotency_key,
            )

            first_status, first_response = first_future.result()
            second_status, second_response = second_future.result()

        assert first_status == 201
        assert second_status == 201

        assert (
            first_response["transaction_key"]
            == second_response["transaction_key"]
        )

        balance_status, balance_response = (
            RequestGenerator.GET_balance(account_key)
        )

        assert balance_status == 200

        # Mesmo com duas requisições simultâneas,
        # R$ 50,00 deve entrar uma única vez.
        assert balance_response["balance"] == "50.00"

        statement_status, statement = (
            RequestGenerator.GET_statement(
                account_key,
                page=1,
                page_size=20,
            )
        )

        assert statement_status == 200
        assert statement["total"] == 1
        assert len(statement["transactions"]) == 1

        assert statement["transactions"][0]["type"] == "deposit"
        assert statement["transactions"][0]["amount"] == "50.00"

    def test_concurrent_opposite_transfers_complete_without_deadlock(self):
        first_account_key = self._create_account(
            "Conta Concorrencia A"
        )

        second_account_key = self._create_account(
            "Conta Concorrencia B"
        )

        first_deposit_status, _ = self._deposit(
            first_account_key,
            "100.00",
        )

        second_deposit_status, _ = self._deposit(
            second_account_key,
            "100.00",
        )

        assert first_deposit_status == 201
        assert second_deposit_status == 201

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                self._transfer,
                first_account_key,
                second_account_key,
                "10.00",
                str(uuid4()),
            )

            second_future = executor.submit(
                self._transfer,
                second_account_key,
                first_account_key,
                "10.00",
                str(uuid4()),
            )

            first_status, _ = first_future.result(timeout=10)
            second_status, _ = second_future.result(timeout=10)

        # As duas operações devem conseguir terminar.
        #
        # O repository bloqueia as contas sempre por Account.id,
        # independentemente do sentido A -> B ou B -> A.
        assert first_status == 201
        assert second_status == 201

        first_balance_status, first_balance = (
            RequestGenerator.GET_balance(first_account_key)
        )

        second_balance_status, second_balance = (
            RequestGenerator.GET_balance(second_account_key)
        )

        assert first_balance_status == 200
        assert second_balance_status == 200

        # Cada conta:
        # começa com 100
        # envia 10 + 0.10 de tarifa
        # recebe 10
        # termina com 99.90
        assert first_balance["balance"] == "99.90"
        assert second_balance["balance"] == "99.90"