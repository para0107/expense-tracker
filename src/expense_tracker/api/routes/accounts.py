import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_account_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.account import (
    AccountResponseModel,
    CreateAccountRequestModel,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
    PageResponseModel,
)
from expense_tracker.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])

AccountServiceDependency = Annotated[AccountService, Depends(get_account_service)]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
NOT_FOUND_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.NOT_FOUND, "The account does not exist or is not the caller's."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=AccountResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "The caller already has an account with this name."
    ),
)
async def create_account(
    request: CreateAccountRequestModel,
    current_user: CurrentUser,
    account_service: AccountServiceDependency,
) -> AccountResponseModel:
    """
    Create an account for the logged-in user.
    """
    return await account_service.create_account(current_user.id, request)


@router.get(
    "",
    response_model=PageResponseModel[AccountResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_accounts(
    current_user: CurrentUser,
    account_service: AccountServiceDependency,
    page: Annotated[
        int, Query(ge=MIN_PAGE, description=f"Page number, starting at {MIN_PAGE}.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=(f"Accounts per page, {MIN_PAGE_SIZE} to {MAX_PAGE_SIZE}."),
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageResponseModel[AccountResponseModel]:
    """
    List the logged-in user's accounts, one page at a time.
    """
    return await account_service.list_accounts(current_user.id, page, page_size)


@router.get(
    "/{account_id}",
    response_model=AccountResponseModel,
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE | VALIDATION_RESPONSE,
)
async def get_account(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    account_service: AccountServiceDependency,
) -> AccountResponseModel:
    """
    Return one of the logged-in user's accounts.
    """
    return await account_service.get_account(current_user.id, account_id)


@router.delete(
    "/{account_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE
    | NOT_FOUND_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "Other records still use the account."
    ),
)
async def delete_account(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    account_service: AccountServiceDependency,
) -> None:
    """
    Delete one of the logged-in user's accounts.
    """
    await account_service.delete_account(current_user.id, account_id)
