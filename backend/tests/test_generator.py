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
                    "category": "troubleshooting",
                    "product": "Router X",
                    "version": "1.0",
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


class WeakLLMClient:
    def generate(self, prompt: str) -> str:
        return "Factory reset"


class MetadataLeakingLLMClient:
    def generate(self, prompt: str) -> str:
        return (
            "[1] | chunk_id=DOC005_C0005 | document_id=DOC005 | "
            "title=Upgrading OpenWrt firmware using LuCI | score=0.8404 "
            "Learn about OpenWrt supported devices."
        )


class PageChromeLeakingLLMClient:
    def generate(self, prompt: str) -> str:
        return (
            "[1] Home Documentation Quick start guide for OpenWrt installation\n\n"
            "[2] Old revisions Backlinks Back to top x Quick start guide for "
            "OpenWrt installation So you want to install OpenWrt on one of your devices."
        )


class InvalidCitationLLMClient:
    def generate(self, prompt: str) -> str:
        return "Hold the reset button for ten seconds and wait for reboot. [2]"


class FailingLLMClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("model unavailable")


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
                    "category": "troubleshooting",
                    "product": "Router X",
                    "version": "1.0",
                    "source_url": "https://example.com/router",
                    "page": 3,
                    "section": "Factory Reset",
                    "text": "Hold the reset button for ten seconds.",
                },
            )
        ],
    )

    assert "Answer this technical support question" in prompt
    assert "Question:" in prompt
    assert "Context:" in prompt
    assert "Answer:" in prompt
    assert "using only the provided support context" in prompt
    assert "Cite every factual claim" in prompt
    assert "Do not expose chunk IDs" in prompt
    assert "How do I reset the router?" in prompt
    assert "Source [1]" in prompt
    assert "Category: troubleshooting" in prompt
    assert "Product: Router X" in prompt
    assert "Version: 1.0" in prompt
    assert "URL: https://example.com/router" in prompt
    assert "chunk_id=" not in prompt
    assert "score=" not in prompt
    assert "Hold the reset button" in prompt


def test_build_grounded_prompt_handles_empty_context_deterministically() -> None:
    prompt = build_grounded_prompt("How do I reset the router?", [])

    assert "No retrieved support context was available." in prompt
    assert prompt.endswith("Answer:")


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
    assert answer.sources[0].product_version == "Router X 1.0"
    assert answer.sources[0].markdown == (
        "[Router Guide - Page 3 - Factory Reset](https://example.com/router)"
    )
    assert "Sources:\n[1] Router Guide - Page 3 - Factory Reset" in (
        answer.answer_with_citations
    )
    assert "Router X 1.0" in answer.answer_with_citations
    assert "https://example.com/router" in answer.answer_with_citations


def test_rag_pipeline_refuses_pricing_questions_before_retrieval() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)

    answer = pipeline.answer("What is the price range for Archer AX55?")

    assert answer.refused is True
    assert answer.no_answer_reason == "unsupported_pricing"
    assert "pricing" in answer.answer
    assert answer.sources == []
    assert retriever.calls == []
    assert llm.prompts == []


def test_rag_pipeline_refuses_purchase_recommendations_before_retrieval() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)

    answer = pipeline.answer("Which router should I buy for my apartment?")

    assert answer.refused is True
    assert answer.no_answer_reason == "unsupported_purchase_recommendation"
    assert "purchasing recommendation" in answer.answer
    assert retriever.calls == []
    assert llm.prompts == []


def test_rag_pipeline_refuses_private_live_state_before_retrieval() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)

    answer = pipeline.answer("What firmware is installed on my router right now?")

    assert answer.refused is True
    assert answer.no_answer_reason == "unsupported_live_state"
    assert "cannot see your live router" in answer.answer
    assert retriever.calls == []
    assert llm.prompts == []


def test_rag_pipeline_refuses_unsafe_access_before_retrieval() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)

    answer = pipeline.answer("Can you hack into my neighbor's Wi-Fi?")

    assert answer.refused is True
    assert answer.no_answer_reason == "unsafe_unauthorized_access"
    assert "unauthorized access" in answer.answer
    assert retriever.calls == []
    assert llm.prompts == []


def test_rag_pipeline_does_not_treat_ip_range_as_pricing() -> None:
    retriever = FakeRetriever()
    llm = FakeLLMClient()
    pipeline = RAGPipeline(retriever=retriever, llm_client=llm)

    answer = pipeline.answer("How do I configure an IP address range?")

    assert answer.refused is False
    assert answer.answer == "Hold the reset button for ten seconds. [1]"
    assert retriever.calls == [("How do I configure an IP address range?", None)]


def test_rag_pipeline_falls_back_to_extractive_answer_for_weak_generation() -> None:
    pipeline = RAGPipeline(retriever=FakeRetriever(), llm_client=WeakLLMClient())

    answer = pipeline.answer("How do I reset Router X?")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert answer.sources[0].chunk_id == "DOC_TEST_C0001"


def test_rag_pipeline_can_skip_llm_generation_for_fast_cited_answers() -> None:
    llm = FakeLLMClient()
    pipeline = RAGPipeline(
        retriever=FakeRetriever(),
        llm_client=llm,
        prompt_config=PromptConfig(llm_generation_enabled=False),
    )

    answer = pipeline.answer("How do I reset Router X?")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert answer.sources[0].chunk_id == "DOC_TEST_C0001"
    assert llm.prompts == []


def test_rag_pipeline_falls_back_when_llm_generation_fails() -> None:
    pipeline = RAGPipeline(
        retriever=FakeRetriever(),
        llm_client=FailingLLMClient(),
        prompt_config=PromptConfig(llm_generation_enabled=True),
    )

    answer = pipeline.answer("How do I reset Router X?")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert answer.sources[0].chunk_id == "DOC_TEST_C0001"


def test_rag_pipeline_falls_back_when_generation_leaks_metadata() -> None:
    pipeline = RAGPipeline(
        retriever=FakeRetriever(),
        llm_client=MetadataLeakingLLMClient(),
    )

    answer = pipeline.answer("Tell me about Router X.")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert "chunk_id=" not in answer.answer
    assert "source_url=" not in answer.answer


def test_rag_pipeline_falls_back_when_generation_leaks_page_chrome() -> None:
    pipeline = RAGPipeline(
        retriever=FakeRetriever(),
        llm_client=PageChromeLeakingLLMClient(),
    )

    answer = pipeline.answer("Guide me through installation.")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert "Home Documentation" not in answer.answer
    assert "Backlinks" not in answer.answer


def test_rag_pipeline_falls_back_when_generation_cites_missing_source() -> None:
    pipeline = RAGPipeline(
        retriever=FakeRetriever(),
        llm_client=InvalidCitationLLMClient(),
    )

    answer = pipeline.answer("How do I reset Router X?")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )


def test_rag_pipeline_fallback_strips_metadata_from_chunk_text() -> None:
    class MetadataTextRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-1",
                    score=0.91,
                    payload={
                        "chunk_id": "DOC_TEST_C0001",
                        "text": (
                            "| chunk_id=DOC_TEST_C0001 | document_id=DOC_TEST | "
                            "title=Router Guide | score=0.9100 "
                            "Hold the reset button for ten seconds."
                        ),
                    },
                )
            ]

    pipeline = RAGPipeline(
        retriever=MetadataTextRetriever(),
        llm_client=WeakLLMClient(),
    )

    answer = pipeline.answer("How do I reset Router X?")

    assert answer.answer == (
        "Based on the available documentation:\n\n"
        "- Hold the reset button for ten seconds. [1]"
    )
    assert "chunk_id=" not in answer.answer
    assert "document_id=" not in answer.answer


def test_rag_pipeline_fallback_removes_document_page_chrome() -> None:
    class OpenWrtInstallRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-1",
                    score=0.91,
                    payload={
                        "chunk_id": "DOC001_C0001",
                        "title": "Quick start guide for OpenWrt installation",
                        "text": (
                            "Home Documentation Quick start guide for OpenWrt "
                            "installation Old revisions Backlinks Back to top x "
                            "So you want to install OpenWrt on one of your devices. "
                            "The following preparation is recommended, before flashing "
                            "OpenWrt firmware: Don't rush the installation, take your time. "
                            "If something seems weird during installation, find answers "
                            "first before continuing. Have your device's precise model "
                            "name and exact hardware version ready."
                        ),
                    },
                )
            ]

    pipeline = RAGPipeline(
        retriever=OpenWrtInstallRetriever(),
        llm_client=WeakLLMClient(),
    )

    answer = pipeline.answer("Guide me through the product installation process.")

    assert "Home Documentation" not in answer.answer
    assert "Backlinks" not in answer.answer
    assert "Based on the available documentation" in answer.answer
    assert "install OpenWrt on one of your devices" in answer.answer
    assert "Don't rush the installation" in answer.answer


def test_rag_pipeline_fallback_skips_vendor_page_chrome() -> None:
    class VendorSetupRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-1",
                    score=0.91,
                    payload={
                        "chunk_id": "DOC024_C0001",
                        "title": "TP-Link router setup",
                        "section": "How to Set Up a TP-Link Router (New Interface)",
                        "text": "How to Set Up a TP-Link Router (New Interface)",
                    },
                ),
                RetrievalResult(
                    point_id="point-2",
                    score=0.9,
                    payload={
                        "chunk_id": "DOC024_C0002",
                        "title": "TP-Link router setup",
                        "section": "When You Set Up",
                        "text": (
                            "How to Set Up a TP-Link Router (New Interface) "
                            "When You Set Up Last updated: September 28, 2026 "
                            "TP-Link routers come with two types of setup interfaces."
                        ),
                    },
                ),
                RetrievalResult(
                    point_id="point-3",
                    score=0.88,
                    payload={
                        "chunk_id": "DOC024_C0003",
                        "title": "TP-Link router setup",
                        "section": "Tether app",
                        "text": (
                            ". This guide walks you through a complete setup using "
                            "the Tether app or the web management page for routers "
                            "with the new interface."
                        ),
                    },
                ),
            ]

    pipeline = RAGPipeline(
        retriever=VendorSetupRetriever(),
        llm_client=WeakLLMClient(),
    )

    answer = pipeline.answer("How do I set up Archer AX55?")

    assert "Last updated" not in answer.answer
    assert "How to Set Up a TP-Link Router (New Interface) [1]" not in answer.answer
    assert "This guide walks you through a complete setup" in answer.answer


def test_rag_pipeline_returns_practical_wifi_troubleshooting_answer() -> None:
    class WifiIssueRetriever(FakeRetriever):
        def retrieve(self, query: str, *, metadata_filter=None):
            return [
                RetrievalResult(
                    point_id="point-1",
                    score=0.71,
                    payload={
                        "chunk_id": "DOC004_C0001",
                        "document_id": "DOC004",
                        "title": "Wi-Fi configuration",
                        "product": "OpenWrt",
                        "category": "configuration",
                        "section": "Bridged AP",
                        "text": (
                            "Wi-Fi configuration Bridged AP Configure access point "
                            "or client mode before changing bridged AP settings."
                        ),
                    },
                ),
                RetrievalResult(
                    point_id="point-2",
                    score=0.76,
                    payload={
                        "chunk_id": "DOC026_C0001",
                        "document_id": "DOC026",
                        "title": "TP-Link Wi-Fi settings and password changes",
                        "product": "TP-Link Routers",
                        "category": "configuration",
                        "section": "Wi-Fi Network Not Showing Up? How to Fix It",
                        "text": (
                            "Please refer to Wi-Fi Network Not Showing Up? How to "
                            "Fix It for detailed troubleshooting guidance."
                        ),
                    },
                ),
                RetrievalResult(
                    point_id="point-3",
                    score=13.9,
                    payload={
                        "chunk_id": "DOC026_C0002",
                        "document_id": "DOC026",
                        "title": "TP-Link Wi-Fi settings and password changes",
                        "product": "TP-Link Routers",
                        "category": "configuration",
                        "section": "Then",
                        "text": (
                            "Disable Smart Connect. Then manually change one of "
                            "the Wi-Fi names (SSID) to something different."
                        ),
                    },
                ),
            ]

    pipeline = RAGPipeline(
        retriever=WifiIssueRetriever(),
        llm_client=WeakLLMClient(),
    )

    answer = pipeline.answer("I face WIFI configuration issue how i solve this")

    assert "general Wi-Fi checks" in answer.answer
    assert "Confirm the Wi-Fi network is enabled" in answer.answer
    assert "Smart Connect" in answer.answer
    assert "Wi-Fi configuration Bridged AP Configure" not in answer.answer


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
    assert answer.answer_with_citations == DEFAULT_NO_ANSWER_RESPONSE
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
    assert answer.answer == DEFAULT_NO_ANSWER_RESPONSE
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
        PromptConfig(llm_generation_timeout_seconds=0)
    except ValueError as error:
        assert "llm_generation_timeout_seconds" in str(error)
    else:
        raise AssertionError("Expected prompt timeout validation error")

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
