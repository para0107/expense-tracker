import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Category

logger = logging.getLogger(__name__)


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_category(self, category: Category) -> Category:
        """
        Insert the category as a new row and return it.
        """
        try:
            self._session.add(category)
            await self._session.flush()
            return category
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not create category_id=%s.", category.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_category_by_id(
        self, user_id: uuid.UUID, category_id: uuid.UUID
    ) -> Category | None:
        """
        Return the user's category with this id, or None when there is none.
        """
        try:
            statement = select(Category).where(
                Category.id == category_id, Category.user_id == user_id
            )
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get category_id=%s.", category_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_categories(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> list[Category]:
        """
        Return one page of the user's categories, ordered by name.
        """
        try:
            statement = (
                select(Category)
                .where(Category.user_id == user_id)
                .order_by(Category.name, Category.id)
                .offset(offset)
                .limit(limit)
            )
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list categories of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def count_categories(self, user_id: uuid.UUID) -> int:
        """
        Return how many categories the user has.
        """
        try:
            statement = (
                select(func.count())
                .select_from(Category)
                .where(Category.user_id == user_id)
            )
            return (await self._session.execute(statement)).scalar_one()
        except SQLAlchemyError as error:
            logger.exception("Could not count categories of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_category(self, user_id: uuid.UUID, category_id: uuid.UUID) -> bool:
        """
        Delete the user's category and return whether a row was deleted.
        """
        try:
            statement = delete(Category).where(
                Category.id == category_id, Category.user_id == user_id
            )
            return (await self._session.execute(statement)).rowcount > 0
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not delete category_id=%s.", category_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
