import logging
import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.budget import (
    BudgetResponseModel,
    BudgetStatusResponseModel,
    CreateBudgetRequestModel,
)
from expense_tracker.repositories.budget_repository import BudgetRepository
from expense_tracker.repositories.category_repository import CategoryRepository
from expense_tracker.schemas import Budget

logger = logging.getLogger(__name__)

MONTHS_PER_YEAR = 12


class BudgetService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_budget(
        self, user_id: uuid.UUID, request: CreateBudgetRequestModel
    ) -> BudgetResponseModel:
        """
        Create a monthly budget for one of the user's categories.

        :param user_id: Owner of the category.
        :param request: Category, year, month and limit of the budget.
        :return: The created budget.
        :raises AppError: NOT_FOUND when the category is missing or not the user's.
        :raises AppError: CONFLICT when the category already has a budget for the month.
        """
        budget = Budget(
            id=uuid.uuid7(),
            category_id=request.category_id,
            month=date(request.year, request.month, 1),
            limit_minor=request.limit_minor,
        )
        try:
            async with self._session_factory.get_session() as session:
                category = await CategoryRepository(session).get_category_by_id(
                    user_id, request.category_id
                )
                if category is None:
                    raise AppError(AppErrorCode.NOT_FOUND)
                await BudgetRepository(session).create_budget(budget)
        except IntegrityError as error:
            logger.warning(
                "Budget rejected, category_id=%s already has one for %s.",
                request.category_id,
                budget.month,
            )
            raise AppError(AppErrorCode.CONFLICT) from error
        return BudgetResponseModel.model_validate(budget)

    async def list_budget_statuses(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> list[BudgetStatusResponseModel]:
        """
        Return the user's budgets of the month with spent, remaining and exceeded.

        :param user_id: Owner of the budgets.
        :param year: Year of the budgets.
        :param month: Month of the budgets.
        :return: One status per budget.
        """
        first_day = date(year, month, 1)
        next_first_day = date(
            year + month // MONTHS_PER_YEAR, month % MONTHS_PER_YEAR + 1, 1
        )
        async with self._session_factory.get_session() as session:
            rows = await BudgetRepository(session).list_budgets_with_spent_minor(
                user_id, first_day, next_first_day
            )
        return [
            BudgetStatusResponseModel(
                **BudgetResponseModel.model_validate(budget).model_dump(),
                spent_minor=spent_minor,
                remaining_minor=budget.limit_minor - spent_minor,
                is_exceeded=spent_minor > budget.limit_minor,
            )
            for budget, spent_minor in rows
        ]

    async def delete_budget(self, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
        """
        Delete the budget of one of the user's categories.

        :param user_id: Owner of the category.
        :param budget_id: Id of the budget.
        :raises AppError: NOT_FOUND when the budget is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            is_deleted = await BudgetRepository(session).delete_budget(
                user_id, budget_id
            )
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)
