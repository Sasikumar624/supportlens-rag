from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.api.errors import ApiErrorCode


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, max_request_bytes: int) -> None:
        super().__init__(app)
        self.max_request_bytes = max_request_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and self._exceeds_limit(content_length):
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "detail": {
                        "code": ApiErrorCode.REQUEST_TOO_LARGE.value,
                        "message": (
                            "Request body exceeds the maximum allowed size of "
                            f"{self.max_request_bytes} bytes."
                        ),
                    }
                },
            )
        return await call_next(request)

    def _exceeds_limit(self, content_length: str) -> bool:
        try:
            return int(content_length) > self.max_request_bytes
        except ValueError:
            return True


def add_security_headers(response: Response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()",
    )
