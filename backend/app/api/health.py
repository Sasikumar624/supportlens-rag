from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_logger


router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/health")
def health_check() -> dict[str, str]:
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }
