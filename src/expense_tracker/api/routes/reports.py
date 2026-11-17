from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_report_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.budget import (
    MAX_BUDGET_MONTH,
    MAX_BUDGET_YEAR,
    MIN_BUDGET_MONTH,
    MIN_BUDGET_YEAR,
    MONTH_DESCRIPTION,
    YEAR_DESCRIPTION,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.report import MonthlyReportResponseModel
from expense_tracker.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]


@router.get(
    "/monthly",
    response_model=MonthlyReportResponseModel,
    status_code=AppStatusCode.OK,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.VALIDATION_ERROR, "The request is not valid."
    ),
)
async def get_monthly_report(
    current_user: CurrentUser,
    report_service: ReportServiceDependency,
    year: Annotated[
        int,
        Query(ge=MIN_BUDGET_YEAR, le=MAX_BUDGET_YEAR, description=YEAR_DESCRIPTION),
    ],
    month: Annotated[
        int,
        Query(ge=MIN_BUDGET_MONTH, le=MAX_BUDGET_MONTH, description=MONTH_DESCRIPTION),
    ],
) -> MonthlyReportResponseModel:
    """
    Return the logged-in user's income, expenses, category totals and top
    descriptions for a month.
    """
    return await report_service.get_monthly_report(current_user.id, year, month)
