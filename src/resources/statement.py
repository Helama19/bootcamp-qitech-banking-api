from fastapi import Query
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import StatementController


class StatementResource:
    def on_get(
        self,
        account_key: str,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> JSONResponse:
        controller = StatementController()

        statement = controller.get_statement(
            account_key=account_key,
            page=page,
            page_size=page_size,
        )

        return JSONResponse(
            content=jsonable_encoder(statement),
            status_code=http_status.HTTP_200_OK,
        )