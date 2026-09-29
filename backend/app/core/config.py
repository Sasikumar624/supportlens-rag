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


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


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
    api_max_request_bytes: int
    api_max_question_chars: int
    qdrant_url: str
    qdrant_api_key: str | None
    qdrant_collection: str
    embedding_model: str
    keyword_retrieval_top_k: int
    keyword_retrieval_min_score: float
    hybrid_retrieval_top_k: int
    hybrid_rrf_k: int
    reranker_model: str
    reranker_candidate_top_k: int
    reranker_final_top_k: int
    llm_provider: str
    llm_model: str | None
    llm_model_type: str
    llm_max_new_tokens: int
    llm_temperature: float
    llm_do_sample: bool
    no_answer_min_score: float
    no_answer_min_context_chars: int


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
        api_max_request_bytes=_get_int("API_MAX_REQUEST_BYTES", 32768),
        api_max_question_chars=_get_int("API_MAX_QUESTION_CHARS", 2000),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "supportlens_chunks"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        keyword_retrieval_top_k=_get_int("KEYWORD_RETRIEVAL_TOP_K", 5),
        keyword_retrieval_min_score=_get_float("KEYWORD_RETRIEVAL_MIN_SCORE", 0.0),
        hybrid_retrieval_top_k=_get_int("HYBRID_RETRIEVAL_TOP_K", 10),
        hybrid_rrf_k=_get_int("HYBRID_RRF_K", 60),
        reranker_model=os.getenv(
            "RERANKER_MODEL",
            "cross-encoder/ms-marco-MiniLM-L6-v2",
        ),
        reranker_candidate_top_k=_get_int("RERANKER_CANDIDATE_TOP_K", 15),
        reranker_final_top_k=_get_int("RERANKER_FINAL_TOP_K", 5),
        llm_provider=os.getenv("LLM_PROVIDER", "local"),
        llm_model=os.getenv("LLM_MODEL") or "Qwen/Qwen2.5-1.5B-Instruct",
        llm_model_type=os.getenv("LLM_MODEL_TYPE", "causal"),
        llm_max_new_tokens=_get_int("LLM_MAX_NEW_TOKENS", 256),
        llm_temperature=_get_float("LLM_TEMPERATURE", 0.0),
        llm_do_sample=_get_bool("LLM_DO_SAMPLE", False),
        no_answer_min_score=_get_float("NO_ANSWER_MIN_SCORE", 0.35),
        no_answer_min_context_chars=_get_int("NO_ANSWER_MIN_CONTEXT_CHARS", 30),
    )
