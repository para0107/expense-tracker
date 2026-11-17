import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import (
    CurrentUser,
    get_recurring_transaction_service,
)
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
from expense_tracker.models.recurring_transaction import (
    CreateRecurringTransactionRequestModel,
    RecurringTransactionResponseModel,
)
from expense_tracker.services.recurring_transaction_service import (
    RecurringTransactionService,
)

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])

RecurringTransactionServiceDependency = Annotated[
    RecurringTransactionService, Depends(get_recurring_transaction_service)
]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=RecurringTransactionResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND,
        "The account or category does not exist or is not the caller's.",
    ),
)
async def create_recurring_transaction(
    request: CreateRecurringTransactionRequestModel,
    current_user: CurrentUser,
    recurring_transaction_service: RecurringTransactionServiceDependency,
) -> RecurringTransactionResponseModel:
    """
    Create a recurring transaction rule for the logged-in user.
    """
    return await recurring_transaction_service.create_recurring_transaction(
        current_user.id, request
    )


@router.get(
    "",
    response_model=PageResponseModel[RecurringTransactionResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_recurring_transactions(
    current_user: CurrentUser,
    recurring_transaction_service: RecurringTransactionServiceDependency,
    page: Annotated[
        int, Query(ge=MIN_PAGE, description=f"Page number, starting at {MIN_PAGE}.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Rules per page, {MIN_PAGE_SIZE} to {MAX_PAGE_SIZE}.",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageResponseModel[RecurringTransactionResponseModel]:
    """
    List the logged-in user's recurring transaction rules, one page at a time.
    """
    return await recurring_transaction_service.list_recurring_transactions(
        current_user.id, page, page_size
    )


@router.delete(
    "/{recurring_transaction_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND, "The rule does not exist or is not the caller's."
    ),
)
async def delete_recurring_transaction(
    recurring_transaction_id: uuid.UUID,
    current_user: CurrentUser,
    recurring_transaction_service: RecurringTransactionServiceDependency,
) -> None:
    """
    Delete one of the logged-in user's recurring transaction rules.
    """
    await recurring_transaction_service.delete_recurring_transaction(
        current_user.id, recurring_transaction_id
    )
