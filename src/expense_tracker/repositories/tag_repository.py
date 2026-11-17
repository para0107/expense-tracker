import logging
import uuid
from collections.abc import Collection

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import Tag

logger = logging.getLogger(__name__)


class TagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_tag(self, tag: Tag) -> Tag:
        """
        Insert the tag as a new row and return it.
        """
        try:
            self._session.add(tag)
            await self._session.flush()
            return tag
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not create tag_id=%s.", tag.id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_tag_by_id(self, user_id: uuid.UUID, tag_id: uuid.UUID) -> Tag | None:
        """
        Return the user's tag with this id, or None when there is none.
        """
        try:
            statement = select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get tag_id=%s.", tag_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_tags(self, user_id: uuid.UUID, offset: int, limit: int) -> list[Tag]:
        """
        Return one page of the user's tags, ordered by name.
        """
        try:
            statement = (
                select(Tag)
                .where(Tag.user_id == user_id)
                .order_by(Tag.name, Tag.id)
                .offset(offset)
                .limit(limit)
            )
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list tags of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def list_tags_by_ids(
        self, user_id: uuid.UUID, tag_ids: Collection[uuid.UUID]
    ) -> list[Tag]:
        """
        Return the user's tags among these ids; ids that are missing or not the user's are left out.
        """
        try:
            statement = select(Tag).where(Tag.user_id == user_id, Tag.id.in_(tag_ids))
            return list((await self._session.execute(statement)).scalars())
        except SQLAlchemyError as error:
            logger.exception("Could not list tags by ids of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def count_tags(self, user_id: uuid.UUID) -> int:
        """
        Return how many tags the user has.
        """
        try:
            statement = (
                select(func.count()).select_from(Tag).where(Tag.user_id == user_id)
            )
            return (await self._session.execute(statement)).scalar_one()
        except SQLAlchemyError as error:
            logger.exception("Could not count tags of user_id=%s.", user_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def delete_tag(self, user_id: uuid.UUID, tag_id: uuid.UUID) -> bool:
        """
        Delete the user's tag and return whether a row was deleted.
        """
        try:
            statement = delete(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
            return (await self._session.execute(statement)).rowcount > 0
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            logger.exception("Could not delete tag_id=%s.", tag_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
