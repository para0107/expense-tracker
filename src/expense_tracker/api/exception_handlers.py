import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.error import ErrorResponseModel

logger = logging.getLogger(__name__)


def build_error_response(error_code: AppErrorCode) -> JSONResponse:
    """
    Build the one error body every failure is answered with.

    :param error_code: Error whose status and message are sent.
    :return: JSON response with the error's status and its code and message.
    """
    detail = error_code.value
    body = ErrorResponseModel(
        code=detail.code, status=detail.status, message=detail.message
    )
    return JSONResponse(
        status_code=detail.status, content=body.model_dump(by_alias=True)
    )


async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    """Answer an AppError with its own code, status and message."""
    return build_error_response(error.error)


async def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Answer invalid input with VALIDATION_ERROR, logging only where it failed."""
    for problem in error.errors():
        logger.warning(
            "Invalid request at loc=%s type=%s.", problem["loc"], problem["type"]
        )
    return build_error_response(AppErrorCode.VALIDATION_ERROR)


async def internal_server_error_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Answer any unexpected exception with INTERNAL_SERVER_ERROR."""
    logger.error("Unhandled error.", exc_info=error)
    return build_error_response(AppErrorCode.INTERNAL_SERVER_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(Exception, internal_server_error_handler)
