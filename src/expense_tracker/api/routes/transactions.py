import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_transaction_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
    PageResponseModel,
)
from expense_tracker.models.transaction import (
    CreateTransactionRequestModel,
    TransactionResponseModel,
)
from expense_tracker.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])

TransactionServiceDependency = Annotated[
    TransactionService, Depends(get_transaction_service)
]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
NOT_FOUND_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.NOT_FOUND, "The transaction does not exist or is not the caller's."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=TransactionResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND,
        "The account, category or a tag does not exist or is not the caller's.",
    ),
)
async def create_transaction(
    request: CreateTransactionRequestModel,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDependency,
) -> TransactionResponseModel:
    """
    Create a transaction for the logged-in user.
    """
    return await transaction_service.create_transaction(current_user.id, request)


@router.get(
    "",
    response_model=PageResponseModel[TransactionResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_transactions(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDependency,
    date_from: Annotated[
        date | None,
        Query(description="First day to include, as YYYY-MM-DD."),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Last day to include, as YYYY-MM-DD."),
    ] = None,
    account_id: Annotated[
        uuid.UUID | None, Query(description="Only transactions of this account.")
    ] = None,
    category_id: Annotated[
        uuid.UUID | None, Query(description="Only transactions of this category.")
    ] = None,
    tag_id: Annotated[
        uuid.UUID | None, Query(description="Only transactions with this tag.")
    ] = None,
    page: Annotated[
        int, Query(ge=MIN_PAGE, description=f"Page number, starting at {MIN_PAGE}.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Transactions per page, {MIN_PAGE_SIZE} to {MAX_PAGE_SIZE}.",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageResponseModel[TransactionResponseModel]:
    """
    List the logged-in user's transactions, newest first, one page at a time.
    """
    return await transaction_service.list_transactions(
        current_user.id,
        date_from,
        date_to,
        account_id,
        category_id,
        tag_id,
        page,
        page_size,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponseModel,
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE | VALIDATION_RESPONSE,
)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDependency,
) -> TransactionResponseModel:
    """
    Return one of the logged-in user's transactions.
    """
    return await transaction_service.get_transaction(current_user.id, transaction_id)


@router.delete(
    "/{transaction_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE | VALIDATION_RESPONSE,
)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDependency,
) -> None:
    """
    Delete one of the logged-in user's transactions.
    """
    await transaction_service.delete_transaction(current_user.id, transaction_id)
