import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Account

logger = logging.getLogger(__name__)


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_account(self, account: Account) -> Account:
        """
        Insert the account as a new row and return it.
        """
        try:
            self._session.add(account)
            await self._session.flush()
            return account
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not create account_id=%s.", account.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_account_by_id(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> Account | None:
        """
        Return the user's account with this id, or None when there is none.
        """
        try:
            statement = select(Account).where(
                Account.id == account_id, Account.user_id == user_id
            )
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get account_id=%s.", account_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_accounts(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> list[Account]:
        """
        Return one page of the user's accounts, ordered by name.
        """
        try:
            statement = (
                select(Account)
                .where(Account.user_id == user_id)
                .order_by(Account.name, Account.id)
                .offset(offset)
                .limit(limit)
            )
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list accounts of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def count_accounts(self, user_id: uuid.UUID) -> int:
        """
        Return how many accounts the user has.
        """
        try:
            statement = select(func.count()).where(Account.user_id == user_id)
            statement = statement.select_from(Account)
            return (await self._session.execute(statement)).scalar_one()
        except SQLAlchemyError as error:
            logger.exception("Could not count accounts of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> bool:
        """
        Delete the user's account and return whether a row was deleted.
        """
        try:
            statement = delete(Account).where(
                Account.id == account_id, Account.user_id == user_id
            )
            return (await self._session.execute(statement)).rowcount > 0
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not delete account_id=%s.", account_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
