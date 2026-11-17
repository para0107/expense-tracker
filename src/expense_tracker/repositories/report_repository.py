import logging
import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Account, Category, Transaction

logger = logging.getLogger(__name__)


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_income_and_expenses_minor(
        self, user_id: uuid.UUID, month: date, next_month: date
    ) -> tuple[int, int]:
        """
        Return the user's income and expenses (as a positive number) in minor units
        for transactions booked from month up to, not including, next_month.
        """
        try:
            statement = self._select_user_transactions(
                func.coalesce(
                    func.sum(Transaction.amount_minor).filter(
                        Transaction.amount_minor > 0
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(-Transaction.amount_minor).filter(
                        Transaction.amount_minor < 0
                    ),
                    0,
                ),
                user_id=user_id,
                month=month,
                next_month=next_month,
            )
            income_minor, expenses_minor = (
                await self._session.execute(statement)
            ).one()
            return int(income_minor), int(expenses_minor)
        except SQLAlchemyError as error:
            logger.exception("Could not total the month of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_expenses_by_category(
        self, user_id: uuid.UUID, month: date, next_month: date
    ) -> list[tuple[uuid.UUID | None, str | None, int]]:
        """
        Return category id, category name and expenses per category, biggest first.
        The uncategorised expenses come back with a null id and name.
        """
        try:
            expenses_minor = func.sum(-Transaction.amount_minor)
            statement = (
                self._select_user_transactions(
                    Transaction.category_id,
                    Category.name,
                    expenses_minor,
                    user_id=user_id,
                    month=month,
                    next_month=next_month,
                )
                .outerjoin(Category, Category.id == Transaction.category_id)
                .where(Transaction.amount_minor < 0)
                .group_by(Transaction.category_id, Category.name)
                .order_by(expenses_minor.desc(), Category.name)
            )
            rows = (await self._session.execute(statement)).all()
            return [(row[0], row[1], int(row[2])) for row in rows]
        except SQLAlchemyError as error:
            logger.exception("Could not group the month of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_top_descriptions_by_expenses(
        self, user_id: uuid.UUID, month: date, next_month: date, limit: int
    ) -> list[tuple[str, int]]:
        """
        Return the descriptions with the highest expenses, biggest first.
        """
        try:
            expenses_minor = func.sum(-Transaction.amount_minor)
            statement = (
                self._select_user_transactions(
                    Transaction.description,
                    expenses_minor,
                    user_id=user_id,
                    month=month,
                    next_month=next_month,
                )
                .where(Transaction.amount_minor < 0)
                .group_by(Transaction.description)
                .order_by(expenses_minor.desc(), Transaction.description)
                .limit(limit)
            )
            rows = (await self._session.execute(statement)).all()
            return [(row[0], int(row[1])) for row in rows]
        except SQLAlchemyError as error:
            logger.exception("Could not rank descriptions of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    def _select_user_transactions(
        self, *columns, user_id: uuid.UUID, month: date, next_month: date
    ) -> Select:
        return (
            select(*columns)
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.user_id == user_id,
                Transaction.booked_on >= month,
                Transaction.booked_on < next_month,
            )
        )
