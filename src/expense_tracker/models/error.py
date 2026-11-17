from typing import Any

from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.base import ResponseModel


class ErrorResponseModel(ResponseModel):
    code: str
    status: int
    message: str

    @classmethod
    def error_response(
        cls, error_code: AppErrorCode, description: str
    ) -> dict[int, dict[str, Any]]:
        """
        Build the entry of a route's `responses` for one error.

        :param error_code: Error whose status the entry is keyed by.
        :param description: When the endpoint answers this error.
        :return: Mapping from the status to the response model and description.
        """
        return {error_code.value.status: {"model": cls, "description": description}}
