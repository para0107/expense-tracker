import logging
import uuid

from sqlalchemy.exc import IntegrityError

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.pagination import PageResponseModel
from expense_tracker.models.tag import CreateTagRequestModel, TagResponseModel
from expense_tracker.repositories.tag_repository import TagRepository
from expense_tracker.schemas import Tag

logger = logging.getLogger(__name__)


class TagService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_tag(
        self, user_id: uuid.UUID, request: CreateTagRequestModel
    ) -> TagResponseModel:
        """
        Create a tag for the user.

        :param user_id: Owner of the new tag.
        :param request: Name of the tag.
        :return: The created tag.
        :raises AppError: CONFLICT when the user already has a tag with this name.
        """
        tag = Tag(id=uuid.uuid7(), user_id=user_id, name=request.name)
        try:
            async with self._session_factory.get_session() as session:
                await TagRepository(session).create_tag(tag)
        except IntegrityError as error:
            logger.warning("Tag rejected, name already used by user_id=%s.", user_id)
            raise AppError(AppErrorCode.CONFLICT) from error
        return TagResponseModel.model_validate(tag)

    async def list_tags(
        self, user_id: uuid.UUID, page: int, page_size: int
    ) -> PageResponseModel[TagResponseModel]:
        """
        Return one page of the user's tags.

        :param user_id: Owner of the tags.
        :param page: Page number, starting at the minimum page.
        :param page_size: Number of tags per page.
        :return: The page of tags.
        """
        async with self._session_factory.get_session() as session:
            repository = TagRepository(session)
            tags = await repository.list_tags(
                user_id, offset=(page - 1) * page_size, limit=page_size
            )
            total_count = await repository.count_tags(user_id)
        return PageResponseModel.create(
            [TagResponseModel.model_validate(tag) for tag in tags],
            page,
            page_size,
            total_count,
        )

    async def get_tag(self, user_id: uuid.UUID, tag_id: uuid.UUID) -> TagResponseModel:
        """
        Return the user's tag.

        :param user_id: Owner of the tag.
        :param tag_id: Id of the tag.
        :return: The tag.
        :raises AppError: NOT_FOUND when the tag is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            tag = await TagRepository(session).get_tag_by_id(user_id, tag_id)
        if tag is None:
            raise AppError(AppErrorCode.NOT_FOUND)
        return TagResponseModel.model_validate(tag)

    async def delete_tag(self, user_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        """
        Delete the user's tag.

        :param user_id: Owner of the tag.
        :param tag_id: Id of the tag.
        :raises AppError: NOT_FOUND when the tag is missing or not the user's.
        :raises AppError: CONFLICT when other rows still reference the tag.
        """
        try:
            async with self._session_factory.get_session() as session:
                is_deleted = await TagRepository(session).delete_tag(user_id, tag_id)
        except IntegrityError as error:
            logger.warning("Tag_id=%s is still referenced.", tag_id)
            raise AppError(AppErrorCode.CONFLICT) from error
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)
