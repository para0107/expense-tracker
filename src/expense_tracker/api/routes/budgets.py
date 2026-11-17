import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_budget_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.budget import (
    MAX_BUDGET_MONTH,
    MAX_BUDGET_YEAR,
    MIN_BUDGET_MONTH,
    MIN_BUDGET_YEAR,
    MONTH_DESCRIPTION,
    YEAR_DESCRIPTION,
    BudgetResponseModel,
    BudgetStatusResponseModel,
    CreateBudgetRequestModel,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])

BudgetServiceDependency = Annotated[BudgetService, Depends(get_budget_service)]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=BudgetResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND, "The category does not exist or is not the caller's."
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "The category already has a budget for the month."
    ),
)
async def create_budget(
    request: CreateBudgetRequestModel,
    current_user: CurrentUser,
    budget_service: BudgetServiceDependency,
) -> BudgetResponseModel:
    """
    Create a monthly budget for one of the logged-in user's categories.
    """
    return await budget_service.create_budget(current_user.id, request)


@router.get(
    "",
    response_model=list[BudgetStatusResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_budget_statuses(
    current_user: CurrentUser,
    budget_service: BudgetServiceDependency,
    year: Annotated[
        int,
        Query(ge=MIN_BUDGET_YEAR, le=MAX_BUDGET_YEAR, description=YEAR_DESCRIPTION),
    ],
    month: Annotated[
        int,
        Query(ge=MIN_BUDGET_MONTH, le=MAX_BUDGET_MONTH, description=MONTH_DESCRIPTION),
    ],
) -> list[BudgetStatusResponseModel]:
    """
    List the logged-in user's budgets of a month with spent, remaining and exceeded.
    """
    return await budget_service.list_budget_statuses(current_user.id, year, month)


@router.delete(
    "/{budget_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND, "The budget does not exist or is not the caller's."
    ),
)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: CurrentUser,
    budget_service: BudgetServiceDependency,
) -> None:
    """
    Delete one of the logged-in user's budgets.
    """
    await budget_service.delete_budget(current_user.id, budget_id)
