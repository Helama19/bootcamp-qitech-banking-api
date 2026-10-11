from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from errors import ClientAlreadyHasAccount, NotFoundClient
from repositories import AccountRepository, ClientRepository


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.client_repository = ClientRepository(self.context)

    def create(self, account_data: dict) -> dict:
        self.logger.debug("Criando uma nova conta")

        client_key = account_data["client_key"]
        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundClient(client_key)

        existing_account = self.account_repository.get_by_client_id(
            client.id
        )

        if existing_account is not None:
            raise ClientAlreadyHasAccount(client_key)

        account = self.account_repository.create(client)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

            existing_account = (
                self.account_repository.get_by_client_id(
                    client.id
                )
            )

            if existing_account is not None:
                raise ClientAlreadyHasAccount(client_key)

            raise

        return {
            "account_key": str(account.account_key),
            "balance": str(account.balance),
            "status": account.status.enumerator,
        }