import uuid

from pydantic import ConfigDict, Field

from expense_tracker.models.base import RequestModel, ResponseModel

MIN_TAG_NAME_LENGTH = 1
MAX_TAG_NAME_LENGTH = 50


class CreateTagRequestModel(RequestModel):
    name: str = Field(
        min_length=MIN_TAG_NAME_LENGTH,
        max_length=MAX_TAG_NAME_LENGTH,
        description=(
            f"Tag name, {MIN_TAG_NAME_LENGTH} to "
            f"{MAX_TAG_NAME_LENGTH} characters, unique per user."
        ),
    )


class TagResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
