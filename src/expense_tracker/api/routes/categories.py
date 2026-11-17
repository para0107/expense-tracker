import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_category_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.category import (
    CategoryResponseModel,
    CreateCategoryRequestModel,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
    PageResponseModel,
)
from expense_tracker.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryServiceDependency = Annotated[CategoryService, Depends(get_category_service)]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
NOT_FOUND_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.NOT_FOUND, "The category does not exist or is not the caller's."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=CategoryResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "The caller already has a category with this name."
    ),
)
async def create_category(
    request: CreateCategoryRequestModel,
    current_user: CurrentUser,
    category_service: CategoryServiceDependency,
) -> CategoryResponseModel:
    """
    Create a category for the logged-in user.
    """
    return await category_service.create_category(current_user.id, request)


@router.get(
    "",
    response_model=PageResponseModel[CategoryResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_categories(
    current_user: CurrentUser,
    category_service: CategoryServiceDependency,
    page: Annotated[
        int, Query(ge=MIN_PAGE, description=f"Page number, starting at {MIN_PAGE}.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Categories per page, {MIN_PAGE_SIZE} to {MAX_PAGE_SIZE}.",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageResponseModel[CategoryResponseModel]:
    """
    List the logged-in user's categories, one page at a time.
    """
    return await category_service.list_categories(current_user.id, page, page_size)


@router.get(
    "/{category_id}",
    response_model=CategoryResponseModel,
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE | VALIDATION_RESPONSE,
)
async def get_category(
    category_id: uuid.UUID,
    current_user: CurrentUser,
    category_service: CategoryServiceDependency,
) -> CategoryResponseModel:
    """
    Return one of the logged-in user's categories.
    """
    return await category_service.get_category(current_user.id, category_id)


@router.delete(
    "/{category_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE
    | NOT_FOUND_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "Other records still use the category."
    ),
)
async def delete_category(
    category_id: uuid.UUID,
    current_user: CurrentUser,
    category_service: CategoryServiceDependency,
) -> None:
    """
    Delete one of the logged-in user's categories.
    """
    await category_service.delete_category(current_user.id, category_id)
