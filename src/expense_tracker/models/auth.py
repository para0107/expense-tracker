import uuid

from pydantic import BaseModel, EmailStr, Field

from expense_tracker.models.base import RequestModel, ResponseModel

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class AccessTokenClaims(BaseModel):
    user_id: uuid.UUID
    family_id: uuid.UUID


class RegisterRequestModel(RequestModel):
    email: EmailStr = Field(description="Login email.")
    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description=(
            f"Password, {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters."
        ),
    )


class LoginRequestModel(RequestModel):
    email: EmailStr = Field(description="Login email.")
    password: str = Field(
        max_length=MAX_PASSWORD_LENGTH, description="Account password."
    )


class UserResponseModel(ResponseModel):
    id: uuid.UUID
    email: str


class IssuedTokensModel(BaseModel):
    access_token: str
    refresh_token: str


class AuthenticatedUserModel(BaseModel):
    id: uuid.UUID
    email: str
    family_id: uuid.UUID
