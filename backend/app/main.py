from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.query import router as query_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import RequestSizeLimitMiddleware, add_security_headers


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_request_bytes=settings.api_max_request_bytes,
)


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    add_security_headers(response)
    return response

app.include_router(health_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(feedback_router)
