from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from utils.schema_handler import SchemaHandler


class ClientResource:
    """Porta de entrada HTTP para operações relacionadas a clientes.

    O resource é responsável somente por:
      1. validar o payload usando o JSON Schema;
      2. chamar o controller;
      3. construir a resposta HTTP.

    As regras de negócio permanecem no ClientController.
    """

    @SchemaHandler.validate("post_client.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ClientController()
        client = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_201_CREATED,
        )