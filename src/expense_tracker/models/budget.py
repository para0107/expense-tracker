import uuid
from datetime import date

from pydantic import ConfigDict, Field

from expense_tracker.models.base import RequestModel, ResponseModel

MIN_BUDGET_YEAR = 2000
MAX_BUDGET_YEAR = 2100
MIN_BUDGET_MONTH = 1
MAX_BUDGET_MONTH = 12

YEAR_DESCRIPTION = f"Year, {MIN_BUDGET_YEAR} to {MAX_BUDGET_YEAR}."
MONTH_DESCRIPTION = f"Month, {MIN_BUDGET_MONTH} to {MAX_BUDGET_MONTH}."


class CreateBudgetRequestModel(RequestModel):
    category_id: uuid.UUID = Field(description="Category the budget limits.")
    year: int = Field(
        ge=MIN_BUDGET_YEAR, le=MAX_BUDGET_YEAR, description=YEAR_DESCRIPTION
    )
    month: int = Field(
        ge=MIN_BUDGET_MONTH, le=MAX_BUDGET_MONTH, description=MONTH_DESCRIPTION
    )
    limit_minor: int = Field(
        gt=0, description="Spending limit for the month in minor units."
    )


class BudgetResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    month: date
    limit_minor: int


class BudgetStatusResponseModel(BudgetResponseModel):
    spent_minor: int
    remaining_minor: int
    is_exceeded: bool
