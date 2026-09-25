from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    app_debug: bool
    log_level: str
    api_host: str
    api_port: int
    api_cors_origins: list[str]
    qdrant_url: str
    qdrant_api_key: str | None
    qdrant_collection: str
    embedding_model: str
    llm_provider: str
    llm_model: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()

    return Settings(
        app_name=os.getenv("APP_NAME", "SupportLens"),
        app_env=os.getenv("APP_ENV", "development"),
        app_debug=_get_bool("APP_DEBUG", True),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=_get_int("API_PORT", 8000),
        api_cors_origins=_get_list("API_CORS_ORIGINS", ["http://localhost:3000"]),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "supportlens_chunks"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        llm_provider=os.getenv("LLM_PROVIDER", "local"),
        llm_model=os.getenv("LLM_MODEL") or None,
    )
