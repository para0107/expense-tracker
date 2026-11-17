from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from expense_tracker.api.exception_handlers import build_error_response
from expense_tracker.api.paths import ACCESS_TOKEN_COOKIE_NAME
from expense_tracker.exceptions.app_error import AppError


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Resolve the caller from the access cookie into request.state.current_user.
        """
        request.state.current_user = None
        access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
        if access_token:
            try:
                request.state.current_user = (
                    await request.app.state.auth_service.get_authenticated_user(
                        access_token
                    )
                )
            except AppError as error:
                return build_error_response(error.error)
        return await call_next(request)
