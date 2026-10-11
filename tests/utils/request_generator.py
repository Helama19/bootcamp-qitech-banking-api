from os import environ

from tests.utils.requisition import ClientRequisition, BaseConnectorResponse


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")


class RequestGenerator:
    @staticmethod
    def POST_client(
        client_payload: dict,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/clients",
            payload=client_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def POST_account(
        account_payload: dict,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/accounts",
            payload=account_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def GET_balance(
        account_key: str,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/accounts/{account_key}/balance",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def GET_statement(
        account_key: str,
        page: int = 1,
        page_size: int = 20,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/accounts/{account_key}/statement",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
            query_params={
                "page": page,
                "page_size": page_size,
            },
        )

        return response.response_status, response.response_json

    @staticmethod
    def PATCH_account_status(
        account_key: str,
        status_payload: dict,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PATCH",
            f"/accounts/{account_key}/status",
            payload=status_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def POST_deposit(
        deposit_payload: dict,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/deposits",
            payload=deposit_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def POST_transfer(
        transfer_payload: dict,
    ) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/transfers",
            payload=transfer_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json