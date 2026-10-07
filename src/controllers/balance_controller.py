from controllers.base_controller import BaseController
from errors import NotFoundAccount
from repositories import AccountRepository


class BalanceController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def get_by_account_key(self, account_key: str) -> dict:
        self.logger.debug("Consultando saldo da conta")

        account = self.account_repository.get_by_key(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        return {
            "account_key": str(account.account_key),
            "balance": str(account.balance),
            "status": account.status.enumerator,
        }