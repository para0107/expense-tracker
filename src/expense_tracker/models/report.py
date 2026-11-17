import uuid

from expense_tracker.models.base import ResponseModel

TOP_DESCRIPTIONS_LIMIT = 5


class CategoryTotalResponseModel(ResponseModel):
    category_id: uuid.UUID | None
    category_name: str | None
    expenses_minor: int


class DescriptionTotalResponseModel(ResponseModel):
    description: str
    expenses_minor: int


class MonthlyReportResponseModel(ResponseModel):
    income_minor: int
    expenses_minor: int
    net_minor: int
    category_totals: list[CategoryTotalResponseModel]
    top_descriptions: list[DescriptionTotalResponseModel]
