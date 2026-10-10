from decimal import Decimal
from uuid import uuid4

from sqlalchemy import or_

from database import Context
from models import FinancialTransaction, TransactionType


class FinancialTransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create_deposit(
        self,
        destination_account_id: int,
        amount,
        idempotency_key: str,
    ) -> FinancialTransaction:
        transaction = FinancialTransaction()

        transaction.transaction_key = str(uuid4())
        transaction.idempotency_key = idempotency_key
        transaction.transaction_type = self.get_type(TransactionType.DEPOSIT)
        transaction.source_account_id = None
        transaction.destination_account_id = destination_account_id
        transaction.amount = amount
        transaction.fee = Decimal("0.00")

        self.session.add(transaction)

        return transaction

    def create_transfer(
        self,
        source_account_id: int,
        destination_account_id: int,
        amount,
        fee,
        idempotency_key: str,
    ) -> FinancialTransaction:
        transaction = FinancialTransaction()

        transaction.transaction_key = str(uuid4())
        transaction.idempotency_key = idempotency_key
        transaction.transaction_type = self.get_type(TransactionType.TRANSFER)
        transaction.source_account_id = source_account_id
        transaction.destination_account_id = destination_account_id
        transaction.amount = amount
        transaction.fee = fee

        self.session.add(transaction)

        return transaction

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> FinancialTransaction:
        return (
            self.session.query(FinancialTransaction)
            .filter(
                FinancialTransaction.idempotency_key == idempotency_key
            )
            .first()
        )

    def get_by_account_id(
        self,
        account_id: int,
        page: int,
        page_size: int,
    ) -> list[FinancialTransaction]:
        offset = (page - 1) * page_size

        return (
            self.session.query(FinancialTransaction)
            .filter(
                or_(
                    FinancialTransaction.source_account_id == account_id,
                    FinancialTransaction.destination_account_id == account_id,
                )
            )
            .order_by(
                FinancialTransaction.created_at.desc(),
                FinancialTransaction.id.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_by_account_id(self, account_id: int) -> int:
        return (
            self.session.query(FinancialTransaction)
            .filter(
                or_(
                    FinancialTransaction.source_account_id == account_id,
                    FinancialTransaction.destination_account_id == account_id,
                )
            )
            .count()
        )

    def get_type(self, type_enumerator: str) -> TransactionType:
        return (
            self.session.query(TransactionType)
            .filter(TransactionType.enumerator == type_enumerator)
            .first()
        )