from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import DepositController
from utils.schema_handler import SchemaHandler


class DepositResource:
    @SchemaHandler.validate("post_deposit.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = DepositController()
        deposit = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(deposit),
            status_code=http_status.HTTP_201_CREATED,
        )