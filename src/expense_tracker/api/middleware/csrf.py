from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from expense_tracker.api.exception_handlers import build_error_response
from expense_tracker.exceptions.error_codes import AppErrorCode

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CROSS_SITE_FETCH_SITE = "cross-site"


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Reject unsafe requests that Sec-Fetch-Site or Origin mark as cross-site.
        """
        if request.method in UNSAFE_METHODS and self._is_cross_site(request):
            return build_error_response(AppErrorCode.CROSS_SITE_REQUEST_REJECTED)
        return await call_next(request)

    def _is_cross_site(self, request: Request) -> bool:
        if request.headers.get("sec-fetch-site") == CROSS_SITE_FETCH_SITE:
            return True
        origin = request.headers.get("origin")
        own_origin = f"{request.url.scheme}://{request.url.netloc}"
        return origin is not None and origin != own_origin
