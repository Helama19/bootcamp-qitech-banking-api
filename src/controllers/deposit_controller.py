from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from errors import (
    AccountCannotReceive,
    IdempotencyConflict,
    InvalidTransactionAmount,
    NotFoundAccount,
)
from models import AccountStatus, TransactionType
from repositories import AccountRepository, FinancialTransactionRepository


class DepositController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = FinancialTransactionRepository(self.context)

    def create(self, deposit_data: dict) -> dict:
        self.logger.debug("Criando um novo depósito")

        account_key = deposit_data["account_key"]
        idempotency_key = deposit_data["idempotency_key"]
        amount = Decimal(deposit_data["amount"])

        if amount <= Decimal("0.00"):
            raise InvalidTransactionAmount(amount)

        existing_transaction = (
            self.transaction_repository.get_by_idempotency_key(
                idempotency_key
            )
        )

        if existing_transaction is not None:
            return self._handle_existing_transaction(
                existing_transaction,
                account_key,
                amount,
                idempotency_key,
            )

        account = self.account_repository.get_by_key_for_update(
            account_key
        )

        if account is None:
            raise NotFoundAccount(account_key)

        existing_transaction = (
            self.transaction_repository.get_by_idempotency_key(
                idempotency_key
            )
        )

        if existing_transaction is not None:
            return self._handle_existing_transaction(
                existing_transaction,
                account_key,
                amount,
                idempotency_key,
            )

        if account.status.enumerator not in (
            AccountStatus.ACTIVE,
            AccountStatus.BLOCKED,
        ):
            raise AccountCannotReceive(
                account_key,
                account.status.enumerator,
            )

        account.balance += amount

        transaction = self.transaction_repository.create_deposit(
            destination_account_id=account.id,
            amount=amount,
            idempotency_key=idempotency_key,
        )

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            existing_transaction = (
                self.transaction_repository.get_by_idempotency_key(
                    idempotency_key
                )
            )

            if existing_transaction is None:
                raise

            return self._handle_existing_transaction(
                existing_transaction,
                account_key,
                amount,
                idempotency_key,
            )

        return self._build_response(
            transaction,
            account_key,
            account.balance,
        )

    def _handle_existing_transaction(
        self,
        transaction,
        account_key: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> dict:
        is_same_deposit = (
            transaction.transaction_type.enumerator
            == TransactionType.DEPOSIT
            and transaction.source_account_id is None
            and str(transaction.destination_account.account_key)
            == account_key
            and transaction.amount == amount
        )

        if not is_same_deposit:
            raise IdempotencyConflict(idempotency_key)

        return self._build_response(
            transaction,
            account_key,
            transaction.destination_account.balance,
        )

    def _build_response(
        self,
        transaction,
        account_key: str,
        balance,
    ) -> dict:
        return {
            "transaction_key": str(transaction.transaction_key),
            "account_key": account_key,
            "type": transaction.transaction_type.enumerator,
            "amount": str(transaction.amount),
            "balance": str(balance),
        }