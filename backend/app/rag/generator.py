from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.rag.retriever import MetadataFilter, RetrievalResult


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        ...


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


@dataclass(frozen=True)
class SourceCitation:
    source_id: int
    chunk_id: str | None
    document_id: str | None
    title: str | None
    page: int | None
    section: str | None
    source_url: str | None
    score: float

    @classmethod
    def from_result(
        cls,
        source_id: int,
        result: RetrievalResult,
    ) -> "SourceCitation":
        return cls(
            source_id=source_id,
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            title=result.title,
            page=result.page,
            section=result.section,
            source_url=result.source_url,
            score=result.score,
        )

    @property
    def label(self) -> str:
        parts = [
            value
            for value in [
                self.title,
                f"Page {self.page}" if self.page is not None else None,
                self.section,
            ]
            if value
        ]
        return " - ".join(parts) if parts else self.chunk_id or f"Source {self.source_id}"


@dataclass(frozen=True)
class GeneratedAnswer:
    question: str
    answer: str
    sources: list[SourceCitation]
    context_chunks: list[RetrievalResult]
    refused: bool = False
    no_answer_reason: str | None = None


@dataclass(frozen=True)
class PromptConfig:
    max_context_chunks: int = 5

    def __post_init__(self) -> None:
        if self.max_context_chunks <= 0:
            raise ValueError("max_context_chunks must be positive")


DEFAULT_NO_ANSWER_RESPONSE = (
    "I could not find information relevant to that question in the available "
    "technical-support documentation."
)


@dataclass(frozen=True)
class NoAnswerConfig:
    enabled: bool = True
    min_context_score: float | None = 0.35
    min_context_chars: int = 30
    response: str = DEFAULT_NO_ANSWER_RESPONSE

    def __post_init__(self) -> None:
        if self.min_context_score is not None and self.min_context_score < 0:
            raise ValueError("min_context_score cannot be negative")
        if self.min_context_chars < 0:
            raise ValueError("min_context_chars cannot be negative")
        if not self.response.strip():
            raise ValueError("response cannot be empty")

    @classmethod
    def from_settings(cls) -> "NoAnswerConfig":
        settings = get_settings()
        return cls(
            min_context_score=settings.no_answer_min_score,
            min_context_chars=settings.no_answer_min_context_chars,
        )


class UnsupportedLLMClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError(
            "No LLM client is configured yet. Phase 16 builds the generation "
            "interface; Phase 17 will wire a local Hugging Face model."
        )


class RAGPipeline:
    def __init__(
        self,
        *,
        retriever: Retriever,
        llm_client: LLMClient | None = None,
        prompt_config: PromptConfig | None = None,
        no_answer_config: NoAnswerConfig | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client or UnsupportedLLMClient()
        self._prompt_config = prompt_config or PromptConfig()
        self._no_answer_config = no_answer_config or NoAnswerConfig()

    def answer(
        self,
        question: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> GeneratedAnswer:
        if not question.strip():
            raise ValueError("question cannot be empty")

        retrieved = self._retriever.retrieve(
            question,
            metadata_filter=metadata_filter,
        )
        context_chunks = retrieved[: self._prompt_config.max_context_chunks]
        no_answer_reason = _no_answer_reason(context_chunks, self._no_answer_config)
        if no_answer_reason is not None:
            return GeneratedAnswer(
                question=question,
                answer=self._no_answer_config.response,
                sources=[],
                context_chunks=context_chunks,
                refused=True,
                no_answer_reason=no_answer_reason,
            )

        prompt = build_grounded_prompt(question, context_chunks)
        answer = self._llm_client.generate(prompt)
        sources = [
            SourceCitation.from_result(index, result)
            for index, result in enumerate(context_chunks, start=1)
        ]
        return GeneratedAnswer(
            question=question,
            answer=answer.strip(),
            sources=sources,
            context_chunks=context_chunks,
        )


def build_grounded_prompt(
    question: str,
    context_chunks: list[RetrievalResult],
) -> str:
    if not question.strip():
        raise ValueError("question cannot be empty")

    context = "\n\n".join(
        _format_context_chunk(index, result)
        for index, result in enumerate(context_chunks, start=1)
    )
    if not context:
        context = "No retrieved support context was available."

    return "\n".join(
        [
            "You are SupportLens, a technical support assistant.",
            "",
            "Answer rules:",
            "- Use only the supplied support context.",
            "- Do not invent unsupported facts.",
            "- If the context is insufficient or irrelevant, say that you could not find relevant information in the available technical-support documentation.",
            "- Prefer concise, practical support steps.",
            "- Preserve warnings, cautions, and important notes.",
            "- Cite supporting sources using bracketed source numbers like [1].",
            "",
            f"User question: {question.strip()}",
            "",
            "Support context:",
            context,
            "",
            "Grounded answer:",
        ]
    )


def _format_context_chunk(index: int, result: RetrievalResult) -> str:
    metadata = [
        f"Source [{index}]",
        f"chunk_id={result.chunk_id}" if result.chunk_id else None,
        f"document_id={result.document_id}" if result.document_id else None,
        f"title={result.title}" if result.title else None,
        f"page={result.page}" if result.page is not None else None,
        f"section={result.section}" if result.section else None,
        f"score={result.score:.4f}",
    ]
    header = " | ".join(value for value in metadata if value)
    return f"{header}\n{result.text}"


def _no_answer_reason(
    context_chunks: list[RetrievalResult],
    config: NoAnswerConfig,
) -> str | None:
    if not config.enabled:
        return None
    if not context_chunks:
        return "no_context"

    total_context_chars = sum(len(result.text.strip()) for result in context_chunks)
    if total_context_chars < config.min_context_chars:
        return "insufficient_context"

    if config.min_context_score is not None:
        best_score = max(result.score for result in context_chunks)
        if best_score < config.min_context_score:
            return "low_relevance"

    return None
