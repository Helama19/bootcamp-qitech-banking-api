from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransferController
from utils.schema_handler import SchemaHandler


class TransferResource:
    @SchemaHandler.validate("post_transfer.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = TransferController()
        transfer = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(transfer),
            status_code=http_status.HTTP_201_CREATED,
        )