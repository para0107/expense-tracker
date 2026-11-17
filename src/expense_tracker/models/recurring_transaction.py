import uuid
from datetime import date
from enum import StrEnum

from pydantic import ConfigDict, Field, field_validator

from expense_tracker.models.base import RequestModel, ResponseModel
from expense_tracker.models.transaction import (
    MAX_AMOUNT_MINOR,
    MAX_DESCRIPTION_LENGTH,
    MIN_AMOUNT_MINOR,
)


class RecurrenceCadence(StrEnum):
    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"


class CreateRecurringTransactionRequestModel(RequestModel):
    account_id: uuid.UUID = Field(description="Account the transactions are booked on.")
    category_id: uuid.UUID | None = Field(
        default=None, description="Category of the transactions, if any."
    )
    amount_minor: int = Field(
        ge=MIN_AMOUNT_MINOR,
        le=MAX_AMOUNT_MINOR,
        description=(
            "Amount in minor units, never zero: "
            "negative is an expense, positive is income."
        ),
    )
    description: str = Field(
        max_length=MAX_DESCRIPTION_LENGTH,
        description=f"Description, at most {MAX_DESCRIPTION_LENGTH} characters.",
    )
    cadence: RecurrenceCadence = Field(description="How often the rule repeats.")
    start_date: date = Field(description="First day the rule applies.")

    @field_validator("amount_minor")
    @classmethod
    def validate_amount_is_not_zero(cls, amount_minor: int) -> int:
        if amount_minor == 0:
            raise ValueError("amount_minor must not be zero")
        return amount_minor


class RecurringTransactionResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    amount_minor: int
    description: str
    cadence: RecurrenceCadence
    start_date: date
