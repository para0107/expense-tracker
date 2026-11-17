from enum import Enum

from pydantic import BaseModel, ConfigDict

from expense_tracker.exceptions.status_codes import AppStatusCode


class ErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    status: AppStatusCode
    message: str


class AppErrorCode(Enum):
    VALIDATION_ERROR = ErrorDetail(
        code="VALIDATION_ERROR",
        status=AppStatusCode.UNPROCESSABLE_CONTENT,
        message="The request is not valid.",
    )
    NOT_FOUND = ErrorDetail(
        code="NOT_FOUND",
        status=AppStatusCode.NOT_FOUND,
        message="The requested resource was not found.",
    )
    CONFLICT = ErrorDetail(
        code="CONFLICT",
        status=AppStatusCode.CONFLICT,
        message="The request conflicts with the current state.",
    )
    UNAUTHORIZED = ErrorDetail(
        code="UNAUTHORIZED",
        status=AppStatusCode.UNAUTHORIZED,
        message="Authentication is required.",
    )
    INVALID_CREDENTIALS = ErrorDetail(
        code="INVALID_CREDENTIALS",
        status=AppStatusCode.UNAUTHORIZED,
        message="The email or password is wrong.",
    )
    INVALID_REFRESH_TOKEN = ErrorDetail(
        code="INVALID_REFRESH_TOKEN",
        status=AppStatusCode.UNAUTHORIZED,
        message="The refresh token is not valid.",
    )
    EMAIL_ALREADY_REGISTERED = ErrorDetail(
        code="EMAIL_ALREADY_REGISTERED",
        status=AppStatusCode.CONFLICT,
        message="This email is already registered.",
    )
    CROSS_SITE_REQUEST_REJECTED = ErrorDetail(
        code="CROSS_SITE_REQUEST_REJECTED",
        status=AppStatusCode.FORBIDDEN,
        message="Cross-site requests are not allowed.",
    )
    CSV_FILE_TOO_LARGE = ErrorDetail(
        code="CSV_FILE_TOO_LARGE",
        status=AppStatusCode.CONTENT_TOO_LARGE,
        message="The CSV file is larger than the allowed size.",
    )
    INVALID_CSV_MAPPING = ErrorDetail(
        code="INVALID_CSV_MAPPING",
        status=AppStatusCode.BAD_REQUEST,
        message="A mapped column is missing from the CSV header.",
    )
    DATABASE_ERROR = ErrorDetail(
        code="DATABASE_ERROR",
        status=AppStatusCode.INTERNAL_SERVER_ERROR,
        message="A database error occurred.",
    )
    DATABASE_UNAVAILABLE = ErrorDetail(
        code="DATABASE_UNAVAILABLE",
        status=AppStatusCode.SERVICE_UNAVAILABLE,
        message="The database is unavailable.",
    )
    INTERNAL_SERVER_ERROR = ErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        status=AppStatusCode.INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred.",
    )
