from uuid import uuid4

from database import Context
from models import Account, AccountStatus, Client


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client: Client) -> Account:
        account = Account()

        account.account_key = str(uuid4())
        account.client_id = client.id
        account.status = self.get_status(AccountStatus.ACTIVE)
        account.balance = 0

        self.session.add(account)

        return account

    def get_by_key(self, account_key: str) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.account_key == account_key)
            .first()
        )

    def get_by_key_for_update(self, account_key: str) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.account_key == account_key)
            .with_for_update()
            .first()
        )

    def get_by_client_id(self, client_id: int) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.client_id == client_id)
            .first()
        )

    def get_status(self, status_enumerator: str) -> AccountStatus:
        return (
            self.session.query(AccountStatus)
            .filter(AccountStatus.enumerator == status_enumerator)
            .first()
        )

    def get_accounts_for_update(
        self,
        source_account_key: str,
        destination_account_key: str,
    ) -> list[Account]:
        return (
            self.session.query(Account)
            .filter(
                Account.account_key.in_(
                    [
                        source_account_key,
                        destination_account_key,
                    ]
                )
            )
            .order_by(Account.id.asc())
            .with_for_update()
            .all()
        )