import uuid

from pydantic import ConfigDict, Field

from expense_tracker.models.base import RequestModel, ResponseModel

MIN_CATEGORY_NAME_LENGTH = 1
MAX_CATEGORY_NAME_LENGTH = 100


class CreateCategoryRequestModel(RequestModel):
    name: str = Field(
        min_length=MIN_CATEGORY_NAME_LENGTH,
        max_length=MAX_CATEGORY_NAME_LENGTH,
        description=(
            f"Category name, {MIN_CATEGORY_NAME_LENGTH} to "
            f"{MAX_CATEGORY_NAME_LENGTH} characters, unique per user."
        ),
    )


class CategoryResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
