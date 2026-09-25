from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }
