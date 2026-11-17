import uuid
from datetime import date

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.models.report import (
    TOP_DESCRIPTIONS_LIMIT,
    CategoryTotalResponseModel,
    DescriptionTotalResponseModel,
    MonthlyReportResponseModel,
)
from expense_tracker.repositories.report_repository import ReportRepository

MONTHS_PER_YEAR = 12


class ReportService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def get_monthly_report(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> MonthlyReportResponseModel:
        """
        Build the user's income, expenses, category totals and top descriptions.

        Amounts are summed across accounts without currency conversion.

        :param user_id: Owner of the transactions.
        :param year: Year of the report.
        :param month: Month of the report.
        :return: The monthly report.
        """
        first_day = date(year, month, 1)
        next_first_day = date(
            year + month // MONTHS_PER_YEAR, month % MONTHS_PER_YEAR + 1, 1
        )
        async with self._session_factory.get_session() as session:
            repository = ReportRepository(session)
            (
                income_minor,
                expenses_minor,
            ) = await repository.get_income_and_expenses_minor(
                user_id, first_day, next_first_day
            )
            category_rows = await repository.list_expenses_by_category(
                user_id, first_day, next_first_day
            )
            description_rows = await repository.list_top_descriptions_by_expenses(
                user_id, first_day, next_first_day, TOP_DESCRIPTIONS_LIMIT
            )
        return MonthlyReportResponseModel(
            income_minor=income_minor,
            expenses_minor=expenses_minor,
            net_minor=income_minor - expenses_minor,
            category_totals=[
                CategoryTotalResponseModel(
                    category_id=category_id,
                    category_name=category_name,
                    expenses_minor=category_expenses_minor,
                )
                for category_id, category_name, category_expenses_minor in category_rows
            ],
            top_descriptions=[
                DescriptionTotalResponseModel(
                    description=description, expenses_minor=description_expenses_minor
                )
                for description, description_expenses_minor in description_rows
            ],
        )
