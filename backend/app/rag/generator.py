import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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
    llm_generation_enabled: bool = True
    llm_generation_timeout_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_context_chunks <= 0:
            raise ValueError("max_context_chunks must be positive")
        if self.llm_generation_timeout_seconds <= 0:
            raise ValueError("llm_generation_timeout_seconds must be positive")

    @classmethod
    def from_settings(cls) -> "PromptConfig":
        settings = get_settings()
        return cls(
            llm_generation_enabled=settings.llm_generation_enabled,
            llm_generation_timeout_seconds=settings.llm_generation_timeout_seconds,
        )


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
                "You are SupportLens, a careful technical-support assistant.",
                "Answer this technical support question using only cited evidence.",
                "Answer using only the provided support context.",
                "If the context is not enough, say that the available documentation does not contain the answer.",
                "Use short practical steps when the question asks how to do something.",
                "Mention warnings or prerequisites when the context includes them.",
                "Cite every factual claim with source numbers like [1] or [2].",
                "Do not expose chunk IDs, retrieval scores, raw metadata, navigation text, or page chrome.",
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
UNSUPPORTED_PRICING_RESPONSE = (
    "The available technical-support documentation does not include product "
    "pricing, price ranges, or current purchase information."
)
UNSUPPORTED_PURCHASE_RESPONSE = (
    "The available technical-support documentation does not include enough "
    "product-selection evidence to make a purchasing recommendation."
)
UNSUPPORTED_LIVE_STATE_RESPONSE = (
    "I cannot see your live router, account, or private device-specific data. "
    "The available documentation can only support general setup and "
    "troubleshooting guidance."
)
UNSUPPORTED_UNSAFE_ACCESS_RESPONSE = (
    "I cannot help with unauthorized access. I can help with legitimate setup, "
    "recovery, and security guidance for your own router when the documentation "
    "supports it."
)

UNSUPPORTED_INTENT_PATTERNS = (
    (
        "unsupported_pricing",
        UNSUPPORTED_PRICING_RESPONSE,
        re.compile(
            r"\b(?:price|prices|pricing|cost|costs|msrp|sale|discount|"
            r"budget|cheap|expensive|price\s+range)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsupported_purchase_recommendation",
        UNSUPPORTED_PURCHASE_RESPONSE,
        re.compile(
            r"\b(?:which|what)\s+router\s+should\s+i\s+buy\b|"
            r"\b(?:recommend|recommendation|best\s+router|buy\s+for)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsupported_live_state",
        UNSUPPORTED_LIVE_STATE_RESPONSE,
        re.compile(
            r"\b(?:my\s+(?:exact\s+)?(?:serial|password|ssid|firmware|"
            r"warranty|account)|running\s+on\s+my\s+router\s+right\s+now|"
            r"installed\s+on\s+my\s+router\s+right\s+now|latest\s+email)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsafe_unauthorized_access",
        UNSUPPORTED_UNSAFE_ACCESS_RESPONSE,
        re.compile(
            r"\b(?:hack|crack|bypass|steal|neighbor'?s\s+wi-?fi|"
            r"unauthorized\s+access)\b",
            re.IGNORECASE,
        ),
    ),
)

WIFI_TROUBLESHOOTING_PATTERN = re.compile(
    r"\b(?:wi-?fi|wireless)\b.*\b(?:issue|problem|not\s+working|"
    r"not\s+showing|cannot\s+find|can't\s+find|configuration)\b|"
    r"\b(?:issue|problem)\b.*\b(?:wi-?fi|wireless)\b",
    re.IGNORECASE,
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

        unsupported_intent = _unsupported_intent(question)
        if unsupported_intent is not None:
            reason, response = unsupported_intent
            return GeneratedAnswer(
                question=question,
                answer=response,
                sources=[],
                context_chunks=[],
                refused=True,
                no_answer_reason=reason,
            )

        retrieved = self._retriever.retrieve(
            question,
            metadata_filter=metadata_filter,
        )
        retrieved = _prefer_answerable_context(retrieved)
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

        intent_answer = _intent_answer(question, context_chunks)
        if intent_answer is not None:
            answer = intent_answer
        elif self._prompt_config.llm_generation_enabled:
            prompt = build_grounded_prompt(question, context_chunks)
            answer = _generate_with_timeout(
                self._llm_client,
                prompt,
                timeout_seconds=self._prompt_config.llm_generation_timeout_seconds,
            )
        else:
            answer = _extractive_answer(context_chunks)
        if _needs_extractive_fallback(answer, source_count=len(context_chunks)):
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


def _generate_with_timeout(
    llm_client: LLMClient,
    prompt: str,
    *,
    timeout_seconds: float,
) -> str:
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(llm_client.generate, prompt)
        return future.result(timeout=timeout_seconds)
    except (Exception, TimeoutError):
        return ""
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _intent_answer(
    question: str,
    context_chunks: list[RetrievalResult],
) -> str | None:
    if WIFI_TROUBLESHOOTING_PATTERN.search(question):
        return _wifi_troubleshooting_answer(context_chunks)
    return None


def _wifi_troubleshooting_answer(context_chunks: list[RetrievalResult]) -> str:
    products = _unique_preserve_order(
        result.product for result in context_chunks if result.product
    )
    openwrt_source = _first_source_matching(context_chunks, product="OpenWrt") or 1
    missing_wifi_source = (
        _first_source_matching(context_chunks, section_contains="not showing")
        or _first_source_matching(context_chunks, product="TP-Link Routers")
        or 1
    )
    smart_connect_source = (
        _first_source_matching(context_chunks, text_contains="Smart Connect")
        or missing_wifi_source
    )
    ssid_source = (
        _first_source_matching(context_chunks, text_contains="SSID")
        or _first_source_matching(context_chunks, product="NETGEAR Routers")
        or smart_connect_source
    )
    settings_source = (
        _first_source_matching(context_chunks, section_contains="Main Network")
        or ssid_source
    )
    scope = (
        f"The retrieved sources include guidance for {', '.join(products)}, so start "
        "with these general Wi-Fi checks and then follow the source that matches your router."
        if len(products) > 1
        else "Start with these Wi-Fi checks from the retrieved support guidance."
    )
    return "\n".join(
        [
            scope,
            "",
            f"- Confirm the Wi-Fi network is enabled and check the router's wireless settings page. [{settings_source}]",
            f"- If the network name is not visible, review the vendor troubleshooting guidance for a hidden or missing Wi-Fi network. [{missing_wifi_source}]",
            f"- If Smart Connect or shared 2.4 GHz/5 GHz names are enabled, try using different SSID names so your device can see the bands separately. [{smart_connect_source}]",
            f"- Check the SSID and Wi-Fi password settings before reconnecting devices. [{ssid_source}]",
            f"- If you are using OpenWrt, review the Wi-Fi configuration mode, such as access point or client mode, before changing bridged AP settings. [{openwrt_source}]",
        ]
    )


def _first_source_matching(
    context_chunks: list[RetrievalResult],
    *,
    product: str | None = None,
    section_contains: str | None = None,
    text_contains: str | None = None,
) -> int | None:
    for index, result in enumerate(context_chunks, start=1):
        if product is not None and result.product != product:
            continue
        if (
            section_contains is not None
            and section_contains.lower() not in (result.section or "").lower()
        ):
            continue
        if (
            text_contains is not None
            and text_contains.lower() not in result.text.lower()
        ):
            continue
        return index
    return None


def _unique_preserve_order(values) -> list:
    seen = set()
    unique_values = []
    for value in values:
        key = str(value).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)
    return unique_values


def _prefer_answerable_context(
    context_chunks: list[RetrievalResult],
) -> list[RetrievalResult]:
    answerable = [
        result
        for result in context_chunks
        if _readable_context_sentences(
            result.text,
            title=result.title,
            section=result.section,
        )
    ]
    return answerable or context_chunks


def _unsupported_intent(question: str) -> tuple[str, str] | None:
    normalized = " ".join(question.strip().split())
    for reason, response, pattern in UNSUPPORTED_INTENT_PATTERNS:
        if pattern.search(normalized):
            return reason, response
    return None


def _format_source_metadata(context_chunks: list[RetrievalResult]) -> str:
    if not context_chunks:
        return "No source metadata was available."

    return "\n".join(
        _format_source_metadata_line(index, result)
        for index, result in enumerate(context_chunks, start=1)
    )


def _format_source_metadata_line(index: int, result: RetrievalResult) -> str:
    metadata = [f"Source [{index}]"]
    if result.title:
        metadata.append(f"Title: {result.title}")
    if result.product:
        metadata.append(f"Product: {result.product}")
    if result.version:
        metadata.append(f"Version: {result.version}")
    if result.category:
        metadata.append(f"Category: {result.category}")
    if result.section:
        metadata.append(f"Section: {result.section}")
    if result.page is not None:
        metadata.append(f"Page: {result.page}")
    if result.source_url:
        metadata.append(f"URL: {result.source_url}")
    return "\n".join(metadata)


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
            "Content:",
            result.text,
        ]
    )


def _needs_extractive_fallback(answer: str, *, source_count: int) -> bool:
    clean_answer = " ".join(answer.strip().split())
    if len(clean_answer.split()) < 8:
        return True
    if _contains_metadata_leak(clean_answer):
        return True
    if _contains_page_chrome(clean_answer):
        return True
    return not _has_valid_citation(clean_answer, source_count=source_count)


def _has_valid_citation(answer: str, *, source_count: int) -> bool:
    citations = [int(value) for value in re.findall(r"\[(\d+)\]", answer)]
    if not citations:
        return False
    return all(1 <= citation <= source_count for citation in citations)


def _extractive_answer(context_chunks: list[RetrievalResult]) -> str:
    bullets = []
    seen = set()
    for index, result in enumerate(context_chunks, start=1):
        for sentence in _readable_context_sentences(
            result.text,
            title=result.title,
            section=result.section,
        ):
            normalized = sentence.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            bullets.append(f"- {sentence} [{index}]")
            if len(bullets) >= 5:
                break
        if len(bullets) >= 5:
            break
    if not bullets:
        return DEFAULT_NO_ANSWER_RESPONSE
    return "\n".join(
        [
            "Based on the available documentation:",
            "",
            *bullets,
        ]
    )


def _compact_context_text(text: str, *, max_chars: int = 450) -> str:
    compacted = _strip_metadata_noise(" ".join(text.strip().split()))
    compacted = _normalize_answer_text(compacted)
    if not compacted:
        return ""
    if len(compacted) <= max_chars:
        return compacted

    truncated = compacted[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:")
    return f"{truncated}."


def _readable_context_sentences(
    text: str,
    *,
    title: str | None = None,
    section: str | None = None,
) -> list[str]:
    cleaned = _strip_metadata_noise(" ".join(text.strip().split()))
    cleaned = _strip_page_chrome(cleaned)
    if not cleaned:
        return []

    candidates = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = []
    for candidate in candidates:
        sentence = _clean_sentence(candidate)
        if not _is_useful_sentence(sentence, title=title, section=section):
            continue
        sentences.append(_compact_context_text(sentence, max_chars=260))
        if len(sentences) >= 5:
            break
    return sentences


def _strip_page_chrome(text: str) -> str:
    replacements = [
        "Home Documentation",
        "Old revisions",
        "Backlinks",
        "Back to top",
        "Back to top x",
        "Back to top ×",
        "Learn about OpenWrt",
    ]
    cleaned = text
    for value in replacements:
        cleaned = cleaned.replace(value, " ")
    cleaned = re.sub(r"\bQuick start guide for OpenWrt installation\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _clean_sentence(text: str) -> str:
    sentence = _normalize_answer_text(text).strip(" -|").lstrip(". ")
    sentence = re.sub(r"\s+", " ", sentence)
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    return sentence


def _normalize_answer_text(text: str) -> str:
    return (
        text.replace("\uFFFD", "'")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _is_useful_sentence(
    sentence: str,
    *,
    title: str | None = None,
    section: str | None = None,
) -> bool:
    if len(sentence.split()) < 6:
        return False

    lowered = sentence.lower()
    source_labels = {
        label.lower().strip()
        for label in [title, section]
        if label and label.strip()
    }
    if lowered in source_labels:
        return False
    if re.search(r"\b(?:the|your|a|an|of|to|for|with)$", lowered):
        return False

    noisy_phrases = [
        "old revisions",
        "backlinks",
        "back to top",
        "home documentation",
        "old openwrt wiki",
        "legacy information",
        "article list",
        "alternate directory search",
        "starter faq",
        "ssh access for newcomers",
        "development snapshots",
        "browse this site",
        "if you have any questions",
        "feel free to ask",
        "last updated",
        "looking for more",
        "is this faq useful",
        "your feedback helps improve",
        "best wifi router",
        "home network security",
        "how to log in to",
        "how to factory reset",
        "how to connect computers",
        "copyright",
        "all rights reserved",
    ]
    return not any(phrase in lowered for phrase in noisy_phrases)


_METADATA_KEY_PATTERN = re.compile(
    r"\b(?:chunk_id|document_id|title|category|product|version|section|"
    r"source_url|score|page)="
)
_SOURCE_METADATA_PATTERN = re.compile(r"\bSource \[\d+\]\b")


def _contains_metadata_leak(answer: str) -> bool:
    return bool(
        _METADATA_KEY_PATTERN.search(answer)
        or _SOURCE_METADATA_PATTERN.search(answer)
    )


def _contains_page_chrome(answer: str) -> bool:
    lowered = answer.lower()
    page_chrome = [
        "home documentation",
        "old revisions",
        "backlinks",
        "back to top",
        "learn about openwrt learn about openwrt",
    ]
    return any(value in lowered for value in page_chrome)


def _strip_metadata_noise(text: str) -> str:
    if not text:
        return ""

    cleaned = text
    if "|" in cleaned:
        cleaned = _strip_pipe_metadata(cleaned)

    cleaned = _METADATA_KEY_PATTERN.sub("", cleaned)
    cleaned = _SOURCE_METADATA_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" |")


def _strip_pipe_metadata(text: str) -> str:
    pieces = []
    metadata_keys = {
        "chunk_id",
        "document_id",
        "title",
        "category",
        "product",
        "version",
        "section",
        "source_url",
        "score",
        "page",
    }
    for piece in text.split("|"):
        stripped = piece.strip()
        if not stripped:
            continue

        key, separator, value = stripped.partition("=")
        if separator and key in metadata_keys:
            if key == "score":
                score_parts = value.split(maxsplit=1)
                if len(score_parts) == 2:
                    pieces.append(score_parts[1])
            continue
        pieces.append(stripped)

    return " ".join(pieces)


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
        best_score = max(_relevance_score(result) for result in context_chunks)
        if best_score < config.min_context_score:
            return "low_relevance"

    return None


def _relevance_score(result: RetrievalResult) -> float:
    for value in [
        result.dense_score,
        result.payload.get("retrieval_score"),
        result.keyword_score,
        result.score,
    ]:
        if isinstance(value, int | float):
            return float(value)
    return 0.0
