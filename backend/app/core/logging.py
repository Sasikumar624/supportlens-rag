import logging
import sys
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


async def log_requests_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    logger = get_logger("app.api.request")
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%.3f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%.3f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
