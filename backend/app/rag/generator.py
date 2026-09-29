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
    category: str | None
    product: str | None
    version: str | None
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
            category=result.category,
            product=result.product,
            version=result.version,
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

    @property
    def product_version(self) -> str | None:
        if self.product and self.version:
            return f"{self.product} {self.version}"
        return self.product or self.version

    @property
    def display_text(self) -> str:
        parts = [
            value
            for value in [
                self.label,
                self.product_version,
                self.source_url,
            ]
            if value
        ]
        return " - ".join(parts)

    @property
    def markdown(self) -> str:
        if self.source_url:
            return f"[{self.label}]({self.source_url})"
        return self.label


@dataclass(frozen=True)
class GeneratedAnswer:
    question: str
    answer: str
    sources: list[SourceCitation]
    context_chunks: list[RetrievalResult]
    refused: bool = False
    no_answer_reason: str | None = None

    @property
    def answer_with_citations(self) -> str:
        if self.refused or not self.sources:
            return self.answer

        source_lines = [
            f"[{source.source_id}] {source.display_text}" for source in self.sources
        ]
        return "\n\n".join([self.answer, "Sources:\n" + "\n".join(source_lines)])


@dataclass(frozen=True)
class PromptConfig:
    max_context_chunks: int = 5

    def __post_init__(self) -> None:
        if self.max_context_chunks <= 0:
            raise ValueError("max_context_chunks must be positive")


@dataclass(frozen=True)
class PromptTemplate:
    def build(
        self,
        question: str,
        context_chunks: list[RetrievalResult],
    ) -> str:
        if not question.strip():
            raise ValueError("question cannot be empty")

        return "\n".join(
            [
                "Answer this technical support question using only the provided context.",
                "If the context is not enough, say that the available documentation does not contain the answer.",
                "Use short practical steps and cite sources with [1], [2], etc.",
                "",
                "Question:",
                question.strip(),
                "",
                "Context:",
                _format_retrieved_context(context_chunks),
                "",
                "Answer:",
            ]
        )


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
        if _needs_extractive_fallback(answer):
            answer = _extractive_answer(context_chunks)
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
    return PromptTemplate().build(question, context_chunks)


def _format_source_metadata(context_chunks: list[RetrievalResult]) -> str:
    if not context_chunks:
        return "No source metadata was available."

    return "\n".join(
        _format_source_metadata_line(index, result)
        for index, result in enumerate(context_chunks, start=1)
    )


def _format_source_metadata_line(index: int, result: RetrievalResult) -> str:
    metadata = [
        f"Source [{index}]",
        f"chunk_id={result.chunk_id}" if result.chunk_id else None,
        f"document_id={result.document_id}" if result.document_id else None,
        f"title={result.title}" if result.title else None,
        f"category={result.category}" if result.category else None,
        f"product={result.product}" if result.product else None,
        f"version={result.version}" if result.version else None,
        f"page={result.page}" if result.page is not None else None,
        f"section={result.section}" if result.section else None,
        f"source_url={result.source_url}" if result.source_url else None,
        f"score={result.score:.4f}",
    ]
    return " | ".join(value for value in metadata if value)


def _format_retrieved_context(context_chunks: list[RetrievalResult]) -> str:
    if not context_chunks:
        return "No retrieved support context was available."

    return "\n\n".join(
        _format_context_chunk(index, result)
        for index, result in enumerate(context_chunks, start=1)
    )


def _format_context_chunk(index: int, result: RetrievalResult) -> str:
    metadata = _format_source_metadata_line(index, result)
    return "\n".join(
        [
            metadata,
            result.text,
        ]
    )


def _needs_extractive_fallback(answer: str) -> bool:
    clean_answer = " ".join(answer.strip().split())
    if len(clean_answer.split()) < 8:
        return True
    return "[" not in clean_answer or "]" not in clean_answer


def _extractive_answer(context_chunks: list[RetrievalResult]) -> str:
    lines = []
    for index, result in enumerate(context_chunks, start=1):
        text = _compact_context_text(result.text)
        if not text:
            continue
        lines.append(f"[{index}] {text}")
        if len(lines) >= 3:
            break
    if not lines:
        return DEFAULT_NO_ANSWER_RESPONSE
    return "\n\n".join(lines)


def _compact_context_text(text: str, *, max_chars: int = 450) -> str:
    compacted = " ".join(text.strip().split())
    if not compacted:
        return ""
    if len(compacted) <= max_chars:
        return compacted

    truncated = compacted[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:")
    return f"{truncated}."


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
