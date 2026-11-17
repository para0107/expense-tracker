import logging
import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Account, RecurringTransaction, Transaction

logger = logging.getLogger(__name__)


class RecurringTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_recurring_transaction(
        self, recurring_transaction: RecurringTransaction
    ) -> RecurringTransaction:
        """
        Insert the recurring rule as a new row and return it.
        """
        try:
            self._session.add(recurring_transaction)
            await self._session.flush()
            return recurring_transaction
        except SQLAlchemyError as error:
            logger.exception(
                "Could not create recurring_transaction_id=%s.",
                recurring_transaction.id,
            )
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_all_recurring_transactions(self) -> list[RecurringTransaction]:
        """
        Return every user's recurring rules.
        """
        try:
            statement = select(RecurringTransaction).order_by(RecurringTransaction.id)
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list all recurring rules.")
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def create_recurring_occurrences(self, rows: list[dict[str, Any]]) -> int:
        """
        Insert generated transactions, ignoring those whose rule already booked that day.

        :param rows: Column values of each transaction to insert.
        :return: How many rows were inserted.
        """
        try:
            statement = (
                insert(Transaction)
                .on_conflict_do_nothing(
                    index_elements=[
                        Transaction.recurring_transaction_id,
                        Transaction.booked_on,
                    ]
                )
                .returning(Transaction.id)
            )
            inserted_ids = (await self._session.execute(statement, rows)).scalars()
            return len(list(inserted_ids))
        except SQLAlchemyError as error:
            logger.exception("Could not insert %s recurring occurrences.", len(rows))
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_recurring_transactions(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> list[RecurringTransaction]:
        """
        Return one page of the user's recurring rules, oldest start date first.
        """
        try:
            statement = (
                select(RecurringTransaction)
                .join(Account, Account.id == RecurringTransaction.account_id)
                .where(Account.user_id == user_id)
                .order_by(RecurringTransaction.start_date, RecurringTransaction.id)
                .offset(offset)
                .limit(limit)
            )
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list recurring rules of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def count_recurring_transactions(self, user_id: uuid.UUID) -> int:
        """
        Return how many recurring rules the user has.
        """
        try:
            statement = (
                select(func.count())
                .select_from(RecurringTransaction)
                .join(Account, Account.id == RecurringTransaction.account_id)
                .where(Account.user_id == user_id)
            )
            return (await self._session.execute(statement)).scalar_one()
        except SQLAlchemyError as error:
            logger.exception("Could not count recurring rules of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_recurring_transaction(
        self, user_id: uuid.UUID, recurring_transaction_id: uuid.UUID
    ) -> bool:
        """
        Delete the user's recurring rule and return whether a row was deleted.
        """
        try:
            user_account_ids = select(Account.id).where(Account.user_id == user_id)
            statement = delete(RecurringTransaction).where(
                RecurringTransaction.id == recurring_transaction_id,
                RecurringTransaction.account_id.in_(user_account_ids),
            )
            return (await self._session.execute(statement)).rowcount > 0
        except SQLAlchemyError as error:
            logger.exception(
                "Could not delete recurring_transaction_id=%s.",
                recurring_transaction_id,
            )
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
