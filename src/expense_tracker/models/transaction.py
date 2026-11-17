import uuid
from datetime import date

from pydantic import ConfigDict, Field, field_validator

from expense_tracker.models.base import RequestModel, ResponseModel
from expense_tracker.models.tag import TagResponseModel

MIN_AMOUNT_MINOR = -(2**63)
MAX_AMOUNT_MINOR = 2**63 - 1
MAX_DESCRIPTION_LENGTH = 500


class CreateTransactionRequestModel(RequestModel):
    account_id: uuid.UUID = Field(description="Account the transaction belongs to.")
    category_id: uuid.UUID | None = Field(
        default=None, description="Category of the transaction, if any."
    )
    tag_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Tags to put on the transaction."
    )
    amount_minor: int = Field(
        ge=MIN_AMOUNT_MINOR,
        le=MAX_AMOUNT_MINOR,
        description=(
            "Amount in minor units, never zero: "
            "negative is an expense, positive is income."
        ),
    )
    booked_on: date = Field(description="Day the transaction happened.")
    description: str = Field(
        max_length=MAX_DESCRIPTION_LENGTH,
        description=f"Description, at most {MAX_DESCRIPTION_LENGTH} characters.",
    )

    @field_validator("amount_minor")
    @classmethod
    def validate_amount_is_not_zero(cls, amount_minor: int) -> int:
        if amount_minor == 0:
            raise ValueError("amount_minor must not be zero")
        return amount_minor


class TransactionResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    amount_minor: int
    booked_on: date
    description: str
    tags: list[TagResponseModel]
