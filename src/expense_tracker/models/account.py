import uuid

from pydantic import ConfigDict, Field

from expense_tracker.models.base import RequestModel, ResponseModel

MIN_ACCOUNT_NAME_LENGTH = 1
MAX_ACCOUNT_NAME_LENGTH = 100
CURRENCY_PATTERN = r"^[A-Z]{3}$"


class CreateAccountRequestModel(RequestModel):
    name: str = Field(
        min_length=MIN_ACCOUNT_NAME_LENGTH,
        max_length=MAX_ACCOUNT_NAME_LENGTH,
        description=(
            f"Account name, {MIN_ACCOUNT_NAME_LENGTH} to "
            f"{MAX_ACCOUNT_NAME_LENGTH} characters, unique per user."
        ),
    )
    currency: str = Field(
        pattern=CURRENCY_PATTERN,
        description="Currency code of three uppercase letters, for example EUR.",
    )


class AccountResponseModel(ResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    currency: str
