from decimal import Decimal

from controllers.base_controller import BaseController
from errors import NotFoundAccount
from repositories import AccountRepository, FinancialTransactionRepository


class StatementController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = FinancialTransactionRepository(
            self.context
        )

    def get_statement(
        self,
        account_key: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        self.logger.debug("Consultando extrato da conta")

        account = self.account_repository.get_by_key(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        transactions = self.transaction_repository.get_by_account_id(
            account_id=account.id,
            page=page,
            page_size=page_size,
        )

        total = self.transaction_repository.count_by_account_id(
            account.id
        )

        transaction_list = []

        for transaction in transactions:
            if transaction.destination_account_id == account.id:
                direction = "IN"
                fee = Decimal("0.00")
                total_amount = transaction.amount
            else:
                direction = "OUT"
                fee = transaction.fee
                total_amount = transaction.amount + transaction.fee

            transaction_list.append(
                {
                    "transaction_key": str(
                        transaction.transaction_key
                    ),
                    "type": transaction.transaction_type.enumerator,
                    "direction": direction,
                    "amount": str(transaction.amount),
                    "fee": str(fee),
                    "total_amount": str(total_amount),
                    "created_at": transaction.created_at.isoformat(),
                }
            )

        return {
            "account_key": str(account.account_key),
            "page": page,
            "page_size": page_size,
            "total": total,
            "transactions": transaction_list,
        }