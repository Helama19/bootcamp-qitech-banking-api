from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import BalanceController


class BalanceResource:
    def on_get(self, account_key: str) -> JSONResponse:
        controller = BalanceController()
        balance = controller.get_by_account_key(account_key)

        return JSONResponse(
            content=jsonable_encoder(balance),
            status_code=http_status.HTTP_200_OK,
        )