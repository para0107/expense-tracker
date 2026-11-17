import logging
import uuid

from sqlalchemy.exc import IntegrityError

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.category import (
    CategoryResponseModel,
    CreateCategoryRequestModel,
)
from expense_tracker.models.pagination import PageResponseModel
from expense_tracker.repositories.category_repository import CategoryRepository
from expense_tracker.schemas import Category

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_category(
        self, user_id: uuid.UUID, request: CreateCategoryRequestModel
    ) -> CategoryResponseModel:
        """
        Create a category for the user.

        :param user_id: Owner of the new category.
        :param request: Name of the category.
        :return: The created category.
        :raises AppError: CONFLICT when the user already has a category with this name.
        """
        category = Category(id=uuid.uuid7(), user_id=user_id, name=request.name)
        try:
            async with self._session_factory.get_session() as session:
                await CategoryRepository(session).create_category(category)
        except IntegrityError as error:
            logger.warning(
                "Category rejected, name already used by user_id=%s.", user_id
            )
            raise AppError(AppErrorCode.CONFLICT) from error
        return CategoryResponseModel.model_validate(category)

    async def list_categories(
        self, user_id: uuid.UUID, page: int, page_size: int
    ) -> PageResponseModel[CategoryResponseModel]:
        """
        Return one page of the user's categories.

        :param user_id: Owner of the categories.
        :param page: Page number, starting at the minimum page.
        :param page_size: Number of categories per page.
        :return: The page of categories.
        """
        async with self._session_factory.get_session() as session:
            repository = CategoryRepository(session)
            categories = await repository.list_categories(
                user_id, offset=(page - 1) * page_size, limit=page_size
            )
            total_count = await repository.count_categories(user_id)
        return PageResponseModel.create(
            [CategoryResponseModel.model_validate(category) for category in categories],
            page,
            page_size,
            total_count,
        )

    async def get_category(
        self, user_id: uuid.UUID, category_id: uuid.UUID
    ) -> CategoryResponseModel:
        """
        Return the user's category.

        :param user_id: Owner of the category.
        :param category_id: Id of the category.
        :return: The category.
        :raises AppError: NOT_FOUND when the category is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            category = await CategoryRepository(session).get_category_by_id(
                user_id, category_id
            )
        if category is None:
            raise AppError(AppErrorCode.NOT_FOUND)
        return CategoryResponseModel.model_validate(category)

    async def delete_category(self, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        """
        Delete the user's category.

        :param user_id: Owner of the category.
        :param category_id: Id of the category.
        :raises AppError: NOT_FOUND when the category is missing or not the user's.
        :raises AppError: CONFLICT when other rows still reference the category.
        """
        try:
            async with self._session_factory.get_session() as session:
                is_deleted = await CategoryRepository(session).delete_category(
                    user_id, category_id
                )
        except IntegrityError as error:
            logger.warning("Category_id=%s is still referenced.", category_id)
            raise AppError(AppErrorCode.CONFLICT) from error
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)
