from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from errors import (
    AccountCannotReceive,
    AccountCannotSend,
    IdempotencyConflict,
    InsufficientBalance,
    InvalidTransactionAmount,
    NotFoundAccount,
    SameAccountTransfer,
)
from models import AccountStatus, TransactionType
from repositories import AccountRepository, FinancialTransactionRepository


class TransferController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = FinancialTransactionRepository(self.context)

    def create(self, transfer_data: dict) -> dict:
        self.logger.debug("Criando uma nova transferência")

        source_account_key = transfer_data["source_account_key"]
        destination_account_key = transfer_data["destination_account_key"]
        idempotency_key = transfer_data["idempotency_key"]
        amount = Decimal(transfer_data["amount"])

        if amount <= Decimal("0.00"):
            raise InvalidTransactionAmount(amount)

        if source_account_key == destination_account_key:
            raise SameAccountTransfer(source_account_key)

        existing_transaction = (
            self.transaction_repository.get_by_idempotency_key(
                idempotency_key
            )
        )

        if existing_transaction is not None:
            return self._handle_existing_transaction(
                existing_transaction,
                source_account_key,
                destination_account_key,
                amount,
                idempotency_key,
            )

        accounts = self.account_repository.get_accounts_for_update(
            source_account_key,
            destination_account_key,
        )

        source_account = None
        destination_account = None

        for account in accounts:
            account_key = str(account.account_key)

            if account_key == source_account_key:
                source_account = account

            if account_key == destination_account_key:
                destination_account = account

        if source_account is None:
            raise NotFoundAccount(source_account_key)

        if destination_account is None:
            raise NotFoundAccount(destination_account_key)

        # Verifica novamente depois de adquirir os locks.
        existing_transaction = (
            self.transaction_repository.get_by_idempotency_key(
                idempotency_key
            )
        )

        if existing_transaction is not None:
            return self._handle_existing_transaction(
                existing_transaction,
                source_account_key,
                destination_account_key,
                amount,
                idempotency_key,
            )

        if source_account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountCannotSend(
                source_account_key,
                source_account.status.enumerator,
            )

        if destination_account.status.enumerator not in (
            AccountStatus.ACTIVE,
            AccountStatus.BLOCKED,
        ):
            raise AccountCannotReceive(
                destination_account_key,
                destination_account.status.enumerator,
            )

        if source_account.balance < amount:
            raise InsufficientBalance(source_account_key)

        source_account.balance -= amount
        destination_account.balance += amount

        transaction = self.transaction_repository.create_transfer(
            source_account_id=source_account.id,
            destination_account_id=destination_account.id,
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
                source_account_key,
                destination_account_key,
                amount,
                idempotency_key,
            )

        return self._build_response(
            transaction,
            source_account,
            destination_account,
        )

    def _handle_existing_transaction(
        self,
        transaction,
        source_account_key: str,
        destination_account_key: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> dict:
        is_same_transfer = (
            transaction.transaction_type.enumerator
            == TransactionType.TRANSFER
            and transaction.source_account_id is not None
            and str(transaction.source_account.account_key)
            == source_account_key
            and str(transaction.destination_account.account_key)
            == destination_account_key
            and transaction.amount == amount
        )

        if not is_same_transfer:
            raise IdempotencyConflict(idempotency_key)

        return self._build_response(
            transaction,
            transaction.source_account,
            transaction.destination_account,
        )

    def _build_response(
        self,
        transaction,
        source_account,
        destination_account,
    ) -> dict:
        return {
            "transaction_key": str(transaction.transaction_key),
            "type": transaction.transaction_type.enumerator,
            "source_account_key": str(source_account.account_key),
            "destination_account_key": str(
                destination_account.account_key
            ),
            "amount": str(transaction.amount),
            "source_balance": str(source_account.balance),
            "destination_balance": str(destination_account.balance),
        }