import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Account, Tag, Transaction

logger = logging.getLogger(__name__)


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        """
        Insert the transaction with its tags as a new row and return it.
        """
        try:
            self._session.add(transaction)
            await self._session.flush()
            return transaction
        except SQLAlchemyError as error:
            logger.exception("Could not create transaction_id=%s.", transaction.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def create_imported_transactions(self, rows: list[dict[str, Any]]) -> int:
        """
        Insert imported rows, ignoring those whose import hash already exists on the account.

        :param rows: Column values of each transaction to insert.
        :return: How many rows were inserted.
        """
        try:
            statement = (
                insert(Transaction)
                .on_conflict_do_nothing(
                    index_elements=[Transaction.account_id, Transaction.import_hash]
                )
                .returning(Transaction.id)
            )
            inserted_ids = (await self._session.execute(statement, rows)).scalars()
            return len(list(inserted_ids))
        except SQLAlchemyError as error:
            logger.exception("Could not insert %s imported transactions.", len(rows))
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_transaction_by_id(
        self, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> Transaction | None:
        """
        Return the user's transaction with this id, or None when there is none.
        """
        try:
            statement = (
                select(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .where(Transaction.id == transaction_id, Account.user_id == user_id)
            )
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get transaction_id=%s.", transaction_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_transactions(
        self,
        user_id: uuid.UUID,
        date_from: date | None,
        date_to: date | None,
        account_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
        tag_id: uuid.UUID | None,
        offset: int,
        limit: int,
    ) -> list[Transaction]:
        """
        Return one page of the user's matching transactions, newest first.
        """
        try:
            statement = (
                select(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .where(
                    *self._build_filters(
                        user_id, date_from, date_to, account_id, category_id, tag_id
                    )
                )
                .order_by(Transaction.booked_on.desc(), Transaction.id)
                .offset(offset)
                .limit(limit)
            )
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list transactions of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def count_transactions(
        self,
        user_id: uuid.UUID,
        date_from: date | None,
        date_to: date | None,
        account_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
        tag_id: uuid.UUID | None,
    ) -> int:
        """
        Return how many of the user's transactions match the filters.
        """
        try:
            statement = (
                select(func.count())
                .select_from(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .where(
                    *self._build_filters(
                        user_id, date_from, date_to, account_id, category_id, tag_id
                    )
                )
            )
            return (await self._session.execute(statement)).scalar_one()
        except SQLAlchemyError as error:
            logger.exception("Could not count transactions of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_transaction(
        self, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> bool:
        """
        Delete the user's transaction and return whether a row was deleted.
        """
        try:
            statement = delete(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.account_id.in_(
                    select(Account.id).where(Account.user_id == user_id)
                ),
            )
            return (await self._session.execute(statement)).rowcount > 0
        except SQLAlchemyError as error:
            logger.exception("Could not delete transaction_id=%s.", transaction_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    def _build_filters(
        self,
        user_id: uuid.UUID,
        date_from: date | None,
        date_to: date | None,
        account_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
        tag_id: uuid.UUID | None,
    ) -> list[ColumnElement[bool]]:
        filters = [Account.user_id == user_id]
        if date_from is not None:
            filters.append(Transaction.booked_on >= date_from)
        if date_to is not None:
            filters.append(Transaction.booked_on <= date_to)
        if account_id is not None:
            filters.append(Transaction.account_id == account_id)
        if category_id is not None:
            filters.append(Transaction.category_id == category_id)
        if tag_id is not None:
            filters.append(Transaction.tags.any(Tag.id == tag_id))
        return filters
