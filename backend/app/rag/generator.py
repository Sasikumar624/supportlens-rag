from dataclasses import dataclass
from typing import Protocol

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


@dataclass(frozen=True)
class PromptConfig:
    max_context_chunks: int = 5

    def __post_init__(self) -> None:
        if self.max_context_chunks <= 0:
            raise ValueError("max_context_chunks must be positive")


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
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client or UnsupportedLLMClient()
        self._prompt_config = prompt_config or PromptConfig()

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
            "- If the context is insufficient, say that the available documentation does not contain enough information.",
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
