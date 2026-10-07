from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountStatusController
from utils.schema_handler import SchemaHandler


class AccountStatusResource:
    @SchemaHandler.validate("patch_account_status.json")
    def on_patch(
        self,
        account_key: str,
        payload: dict,
    ) -> JSONResponse:
        controller = AccountStatusController()

        account = controller.update(
            account_key=account_key,
            status_data=payload,
        )

        return JSONResponse(
            content=jsonable_encoder(account),
            status_code=http_status.HTTP_200_OK,
        )