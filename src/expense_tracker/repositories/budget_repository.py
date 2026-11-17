import logging
import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Budget, Category, Transaction

logger = logging.getLogger(__name__)


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_budget(self, budget: Budget) -> Budget:
        """
        Insert the budget as a new row and return it.
        """
        try:
            self._session.add(budget)
            await self._session.flush()
            return budget
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not create budget_id=%s.", budget.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_budgets_with_spent_minor(
        self, user_id: uuid.UUID, month: date, next_month: date
    ) -> list[tuple[Budget, int]]:
        """
        Return the user's budgets of the month with the sum of their expenses
        booked from month up to, not including, next_month.
        """
        try:
            spent_minor = func.coalesce(func.sum(-Transaction.amount_minor), 0)
            statement = (
                select(Budget, spent_minor)
                .join(Category, Category.id == Budget.category_id)
                .outerjoin(
                    Transaction,
                    (Transaction.category_id == Budget.category_id)
                    & (Transaction.amount_minor < 0)
                    & (Transaction.booked_on >= month)
                    & (Transaction.booked_on < next_month),
                )
                .where(Category.user_id == user_id, Budget.month == month)
                .group_by(Budget.id)
                .order_by(Budget.id)
            )
            rows = (await self._session.execute(statement)).all()
            return [(budget, int(spent)) for budget, spent in rows]
        except SQLAlchemyError as error:
            logger.exception("Could not list budgets of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_budget(self, user_id: uuid.UUID, budget_id: uuid.UUID) -> bool:
        """
        Delete the user's budget and return whether a row was deleted.
        """
        try:
            user_category_ids = select(Category.id).where(Category.user_id == user_id)
            statement = delete(Budget).where(
                Budget.id == budget_id, Budget.category_id.in_(user_category_ids)
            )
            return (await self._session.execute(statement)).rowcount > 0
        except SQLAlchemyError as error:
            logger.exception("Could not delete budget_id=%s.", budget_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
