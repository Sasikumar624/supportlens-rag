from app.rag.generator import (
    DEFAULT_NO_ANSWER_RESPONSE,
    NoAnswerConfig,
    PromptConfig,
    RAGPipeline,
    UnsupportedLLMClient,
    build_grounded_prompt,
)
from app.rag.retriever import MetadataFilter, RetrievalResult


class FakeRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, MetadataFilter | None]] = []

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append((query, metadata_filter))
        return [
            RetrievalResult(
                point_id="point-1",
                score=0.91,
                payload={
                    "chunk_id": "DOC_TEST_C0001",
                    "document_id": "DOC_TEST",
                    "title": "Router Guide",
                    "source_url": "https://example.com/router",
                    "page": 3,
                    "section": "Factory Reset",
                    "text": "Hold the reset button for ten seconds.",
                },
            )
        ]


class FakeLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "Hold the reset button for ten seconds. [1]"


def test_build_grounded_prompt_includes_rules_question_and_context() -> None:
    prompt = build_grounded_prompt(
        "How do I reset the router?",
        [
            RetrievalResult(
                point_id="point-1",
                score=0.91,
                payload={
                    "chunk_id": "DOC_TEST_C0001",
                    "document_id": "DOC_TEST",
                    "title": "Router Guide",
                    "page": 3,
                    "section": "Factory Reset",
                    "text": "Hold the reset button for ten seconds.",
                },
            )
        ],
    )

    assert "Use only the supplied support context" in prompt
    assert "Do not invent unsupported facts" in prompt
    assert "How do I reset the router?" in prompt
    assert "Source [1]" in prompt
    assert "Hold the reset button" in prompt


def test_rag_pipeline_retrieves_builds_prompt_and_returns_sources() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)
    metadata_filter = MetadataFilter(product="Router X")

    answer = pipeline.answer(
        "How do I reset Router X?",
        metadata_filter=metadata_filter,
    )

    assert retriever.calls == [("How do I reset Router X?", metadata_filter)]
    assert len(llm.prompts) == 1
    assert answer.answer == "Hold the reset button for ten seconds. [1]"
    assert answer.sources[0].source_id == 1
    assert answer.sources[0].chunk_id == "DOC_TEST_C0001"
    assert answer.sources[0].label == "Router Guide - Page 3 - Factory Reset"


def test_rag_pipeline_limits_context_chunks() -> None:
    class ManyResultsRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id=f"point-{index}",
                    score=0.9,
                    payload={
                        "chunk_id": f"DOC_TEST_C{index:04d}",
                        "text": f"Context {index}",
                    },
                )
                for index in range(1, 4)
            ]

    llm = FakeLLMClient()
    pipeline = RAGPipeline(
        retriever=ManyResultsRetriever(),
        llm_client=llm,
        prompt_config=PromptConfig(max_context_chunks=2),
        no_answer_config=NoAnswerConfig(min_context_chars=1),
    )

    answer = pipeline.answer("Question?")

    assert len(answer.context_chunks) == 2
    assert "Context 1" in llm.prompts[0]
    assert "Context 2" in llm.prompts[0]
    assert "Context 3" not in llm.prompts[0]


def test_rag_pipeline_refuses_when_no_context_is_retrieved() -> None:
    class EmptyRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            self.calls.append((query, metadata_filter))
            return []

    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=EmptyRetriever(), llm_client=llm)

    answer = pipeline.answer("Who won yesterday's football match?")

    assert answer.refused is True
    assert answer.no_answer_reason == "no_context"
    assert answer.answer == DEFAULT_NO_ANSWER_RESPONSE
    assert answer.sources == []
    assert llm.prompts == []


def test_rag_pipeline_refuses_low_relevance_context_before_generation() -> None:
    class LowScoreRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-low",
                    score=0.12,
                    payload={
                        "chunk_id": "DOC_TEST_C0002",
                        "text": "This support article explains how to mount a router.",
                    },
                )
            ]

    llm = FakeLLMClient()
    pipeline = RAGPipeline(
        retriever=LowScoreRetriever(),
        llm_client=llm,
        no_answer_config=NoAnswerConfig(min_context_score=0.5),
    )

    answer = pipeline.answer("What was the score in the football match?")

    assert answer.refused is True
    assert answer.no_answer_reason == "low_relevance"
    assert llm.prompts == []


def test_rag_pipeline_refuses_when_context_is_too_thin() -> None:
    class ThinContextRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-thin",
                    score=0.9,
                    payload={"chunk_id": "DOC_TEST_C0003", "text": "Reset."},
                )
            ]

    llm = FakeLLMClient()
    pipeline = RAGPipeline(
        retriever=ThinContextRetriever(),
        llm_client=llm,
        no_answer_config=NoAnswerConfig(min_context_chars=20),
    )

    answer = pipeline.answer("How do I reset the router?")

    assert answer.refused is True
    assert answer.no_answer_reason == "insufficient_context"
    assert llm.prompts == []


def test_rag_pipeline_can_disable_no_answer_gate_for_experiments() -> None:
    class EmptyRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return []

    llm = FakeLLMClient()
    pipeline = RAGPipeline(
        retriever=EmptyRetriever(),
        llm_client=llm,
        no_answer_config=NoAnswerConfig(enabled=False),
    )

    answer = pipeline.answer("Question?")

    assert answer.refused is False
    assert answer.answer == "Hold the reset button for ten seconds. [1]"
    assert len(llm.prompts) == 1


def test_generation_validates_empty_question_and_missing_llm() -> None:
    pipeline = RAGPipeline(retriever=FakeRetriever(), llm_client=FakeLLMClient())

    try:
        pipeline.answer(" ")
    except ValueError as error:
        assert "question" in str(error)
    else:
        raise AssertionError("Expected empty question validation error")

    try:
        UnsupportedLLMClient().generate("prompt")
    except RuntimeError as error:
        assert "No LLM client" in str(error)
    else:
        raise AssertionError("Expected unsupported LLM error")

    try:
        PromptConfig(max_context_chunks=0)
    except ValueError as error:
        assert "max_context_chunks" in str(error)
    else:
        raise AssertionError("Expected prompt config validation error")

    try:
        NoAnswerConfig(min_context_score=-0.1)
    except ValueError as error:
        assert "min_context_score" in str(error)
    else:
        raise AssertionError("Expected no-answer score validation error")

    try:
        NoAnswerConfig(min_context_chars=-1)
    except ValueError as error:
        assert "min_context_chars" in str(error)
    else:
        raise AssertionError("Expected no-answer context validation error")
