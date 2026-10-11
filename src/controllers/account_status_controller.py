from decimal import Decimal

from controllers.base_controller import BaseController
from errors import (
    AccountCannotChangeStatus,
    AccountMustHaveZeroBalance,
    NotFoundAccount,
)
from models import AccountStatus
from repositories import AccountRepository


class AccountStatusController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def update(
        self,
        account_key: str,
        status_data: dict,
    ) -> dict:
        self.logger.debug("Alterando status da conta")

        new_status = status_data["status"]

        account = self.account_repository.get_by_key_for_update(
            account_key
        )

        if account is None:
            raise NotFoundAccount(account_key)

        current_status = account.status.enumerator

        if current_status == new_status:
            return self._build_response(account)

        if current_status == AccountStatus.CLOSED:
            raise AccountCannotChangeStatus(
                current_status,
                new_status,
            )

        if (
            new_status == AccountStatus.CLOSED
            and account.balance != Decimal("0.00")
        ):
            raise AccountMustHaveZeroBalance(account_key)

        new_account_status = self.account_repository.get_status(
            new_status
        )

        account.status = new_account_status

        self.session.commit()

        return self._build_response(account)

    def _build_response(self, account) -> dict:
        return {
            "account_key": str(account.account_key),
            "status": account.status.enumerator,
            "balance": str(account.balance),
        }