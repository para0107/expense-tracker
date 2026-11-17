import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from expense_tracker.api.dependencies import CurrentUser, get_tag_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
    PageResponseModel,
)
from expense_tracker.models.tag import CreateTagRequestModel, TagResponseModel
from expense_tracker.services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])

TagServiceDependency = Annotated[TagService, Depends(get_tag_service)]

UNAUTHORIZED_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
)
NOT_FOUND_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.NOT_FOUND, "The tag does not exist or is not the caller's."
)
VALIDATION_RESPONSE = ErrorResponseModel.error_response(
    AppErrorCode.VALIDATION_ERROR, "The request is not valid."
)


@router.post(
    "",
    response_model=TagResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=UNAUTHORIZED_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "The caller already has a tag with this name."
    ),
)
async def create_tag(
    request: CreateTagRequestModel,
    current_user: CurrentUser,
    tag_service: TagServiceDependency,
) -> TagResponseModel:
    """
    Create a tag for the logged-in user.
    """
    return await tag_service.create_tag(current_user.id, request)


@router.get(
    "",
    response_model=PageResponseModel[TagResponseModel],
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | VALIDATION_RESPONSE,
)
async def list_tags(
    current_user: CurrentUser,
    tag_service: TagServiceDependency,
    page: Annotated[
        int, Query(ge=MIN_PAGE, description=f"Page number, starting at {MIN_PAGE}.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Tags per page, {MIN_PAGE_SIZE} to {MAX_PAGE_SIZE}.",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageResponseModel[TagResponseModel]:
    """
    List the logged-in user's tags, one page at a time.
    """
    return await tag_service.list_tags(current_user.id, page, page_size)


@router.get(
    "/{tag_id}",
    response_model=TagResponseModel,
    status_code=AppStatusCode.OK,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE | VALIDATION_RESPONSE,
)
async def get_tag(
    tag_id: uuid.UUID, current_user: CurrentUser, tag_service: TagServiceDependency
) -> TagResponseModel:
    """
    Return one of the logged-in user's tags.
    """
    return await tag_service.get_tag(current_user.id, tag_id)


@router.delete(
    "/{tag_id}",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSE
    | NOT_FOUND_RESPONSE
    | VALIDATION_RESPONSE
    | ErrorResponseModel.error_response(
        AppErrorCode.CONFLICT, "Other records still use the tag."
    ),
)
async def delete_tag(
    tag_id: uuid.UUID, current_user: CurrentUser, tag_service: TagServiceDependency
) -> None:
    """
    Delete one of the logged-in user's tags.
    """
    await tag_service.delete_tag(current_user.id, tag_id)
