from fastapi import FastAPI

from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import (
    AccountResource,
    AccountStatusResource,
    BalanceResource,
    ClientResource,
    DepositResource,
    HealthCheckResource,
    SampleEntityResource,
    StatementResource,
    TransferResource,
)
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Middlewares
    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    # Resources
    health_check_resource = HealthCheckResource()
    sample_entity_resource = SampleEntityResource()
    client_resource = ClientResource()
    account_resource = AccountResource()
    deposit_resource = DepositResource()
    transfer_resource = TransferResource()
    balance_resource = BalanceResource()
    statement_resource = StatementResource()
    account_status_resource = AccountStatusResource()

    # Health check
    application.add_api_route(
        "/",
        health_check_resource.on_get_home,
        methods=["GET"],
    )

    application.add_api_route(
        "/health_check",
        health_check_resource.on_get_health_check,
        methods=["GET"],
    )

    # Sample Entity - rotas originais do projeto-base
    application.add_api_route(
        "/sample_entity",
        sample_entity_resource.on_post,
        methods=["POST"],
    )

    application.add_api_route(
        "/sample_entity/{sample_entity_key}",
        sample_entity_resource.on_get_by_key,
        methods=["GET"],
    )

    application.add_api_route(
        "/sample_entity/{sample_entity_key}",
        sample_entity_resource.on_put_by_key,
        methods=["PUT"],
    )

    application.add_api_route(
        "/webhook/sample_entity/{sample_entity_key}/increment_counter",
        sample_entity_resource.on_put_increment_counter,
        methods=["PUT"],
    )

    application.add_api_route(
        "/sample_entities",
        sample_entity_resource.on_get_list,
        methods=["GET"],
    )

    # Clients
    application.add_api_route(
        "/clients",
        client_resource.on_post,
        methods=["POST"],
    )

    # Accounts
    application.add_api_route(
        "/accounts",
        account_resource.on_post,
        methods=["POST"],
    )

    # Account status
    application.add_api_route(
        "/accounts/{account_key}/status",
        account_status_resource.on_patch,
        methods=["PATCH"],
    )

    # Balance
    application.add_api_route(
        "/accounts/{account_key}/balance",
        balance_resource.on_get,
        methods=["GET"],
    )

    # Statement
    application.add_api_route(
        "/accounts/{account_key}/statement",
        statement_resource.on_get,
        methods=["GET"],
    )

    # Deposits
    application.add_api_route(
        "/deposits",
        deposit_resource.on_post,
        methods=["POST"],
    )

    # Transfers
    application.add_api_route(
        "/transfers",
        transfer_resource.on_post,
        methods=["POST"],
    )

    # Error handlers
    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()