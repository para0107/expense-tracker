import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, user: User) -> User:
        """
        Insert the user as a new row and return it.
        """
        try:
            self._session.add(user)
            await self._session.flush()
            return user
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not create user_id=%s.", user.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Return the user with this email, or None when there is none.
        """
        try:
            statement = select(User).where(User.email == email)
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get user by email.")
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Return the user with this id, or None when there is none.
        """
        try:
            return await self._session.get(User, user_id)
        except SQLAlchemyError as error:
            logger.exception("Could not get user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
