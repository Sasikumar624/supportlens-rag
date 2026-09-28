from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence, QuestionCategory
from app.evaluation.system_comparison import (
    BASELINE_PROFILE,
    IMPROVED_PROFILE,
    SystemProfile,
    SystemUnderEvaluation,
    compare_systems,
)
from app.rag.generator import GeneratedAnswer, SourceCitation
from app.rag.retriever import RetrievalResult


class FakeRetriever:
    def __init__(self, results_by_query: dict[str, list[RetrievalResult]]) -> None:
        self.results_by_query = results_by_query
        self.calls: list[str] = []

    def retrieve(self, query: str) -> list[RetrievalResult]:
        self.calls.append(query)
        return self.results_by_query.get(query, [])


class FakePipeline:
    def __init__(self, answers_by_question: dict[str, GeneratedAnswer]) -> None:
        self.answers_by_question = answers_by_question
        self.calls: list[str] = []

    def answer(self, question: str) -> GeneratedAnswer:
        self.calls.append(question)
        return self.answers_by_question[question]


def question(
    question_id: str,
    text: str,
    expected_document_id: str,
) -> EvaluationQuestion:
    return EvaluationQuestion(
        question_id=question_id,
        question=text,
        category=QuestionCategory.TROUBLESHOOTING,
        answerable=True,
        expected_evidence=[
            ExpectedEvidence(
                document_id=expected_document_id,
                required_terms=["reset button"],
            )
        ],
    )


def result(document_id: str, text: str = "Hold the reset button.") -> RetrievalResult:
    return RetrievalResult(
        point_id=f"{document_id}_POINT",
        score=0.9,
        payload={
            "document_id": document_id,
            "chunk_id": f"{document_id}_C0001",
            "title": f"{document_id} Guide",
            "text": text,
        },
    )


def source(source_id: int, document_id: str) -> SourceCitation:
    return SourceCitation(
        source_id=source_id,
        chunk_id=f"{document_id}_C0001",
        document_id=document_id,
        title=f"{document_id} Guide",
        category=None,
        product=None,
        version=None,
        page=None,
        section=None,
        source_url=None,
        score=0.9,
    )


def answer(
    text: str,
    context: list[RetrievalResult],
    sources: list[SourceCitation],
) -> GeneratedAnswer:
    return GeneratedAnswer(
        question="Question?",
        answer=text,
        sources=sources,
        context_chunks=context,
    )


def test_compare_systems_reports_baseline_improved_and_metric_deltas() -> None:
    questions = [question("Q1", "How do I reset Router X?", "DOC_RESET")]
    baseline_retriever = FakeRetriever(
        {"How do I reset Router X?": [result("DOC_OTHER"), result("DOC_RESET")]}
    )
    improved_retriever = FakeRetriever(
        {"How do I reset Router X?": [result("DOC_RESET"), result("DOC_OTHER")]}
    )
    baseline_pipeline = FakePipeline(
        {
            "How do I reset Router X?": answer(
                "Hold reset. [2]",
                [result("DOC_OTHER"), result("DOC_RESET")],
                [source(1, "DOC_OTHER"), source(2, "DOC_RESET")],
            )
        }
    )
    improved_pipeline = FakePipeline(
        {
            "How do I reset Router X?": answer(
                "Hold the reset button. [1]",
                [result("DOC_RESET"), result("DOC_OTHER")],
                [source(1, "DOC_RESET"), source(2, "DOC_OTHER")],
            )
        }
    )

    report = compare_systems(
        questions,
        baseline=SystemUnderEvaluation(
            profile=BASELINE_PROFILE,
            retriever=baseline_retriever,
            pipeline=baseline_pipeline,
        ),
        improved=SystemUnderEvaluation(
            profile=IMPROVED_PROFILE,
            retriever=improved_retriever,
            pipeline=improved_pipeline,
        ),
    )

    assert report.baseline.profile.name == "baseline"
    assert report.improved.profile.name == "improved"
    assert report.baseline.retrieval.metrics.mrr == 0.5
    assert report.improved.retrieval.metrics.mrr == 1.0

    retrieval_deltas = {
        delta.metric_name: delta for delta in report.retrieval_deltas
    }
    generation_deltas = {
        delta.metric_name: delta for delta in report.generation_deltas
    }
    assert retrieval_deltas["mrr"].absolute_delta == 0.5
    assert retrieval_deltas["recall_at_1"].absolute_delta == 1.0
    assert generation_deltas["average_answer_relevance"].absolute_delta == 1.0
    assert generation_deltas["average_overall_score"].absolute_delta > 0.0
    assert baseline_retriever.calls == ["How do I reset Router X?"]
    assert improved_pipeline.calls == ["How do I reset Router X?"]


def test_system_profiles_document_baseline_and_improved_capabilities() -> None:
    assert BASELINE_PROFILE.features == (
        "basic_chunking",
        "dense_retrieval",
        "top_5_context",
        "llm_generation",
    )
    assert "hybrid_fusion" in IMPROVED_PROFILE.features
    assert "no_answer_handling" in IMPROVED_PROFILE.features
    assert "citations" in IMPROVED_PROFILE.features


def test_compare_systems_validates_inputs() -> None:
    valid_question = question("Q1", "reset", "DOC_RESET")
    system = SystemUnderEvaluation(
        profile=BASELINE_PROFILE,
        retriever=FakeRetriever({"reset": [result("DOC_RESET")]}),
        pipeline=FakePipeline(
            {
                "reset": answer(
                    "Hold the reset button. [1]",
                    [result("DOC_RESET")],
                    [source(1, "DOC_RESET")],
                )
            }
        ),
    )

    try:
        compare_systems([], baseline=system, improved=system)
    except ValueError as error:
        assert "questions" in str(error)
    else:
        raise AssertionError("Expected questions validation error")

    try:
        compare_systems([valid_question], baseline=system, improved=system)
    except ValueError as error:
        assert "profile names" in str(error)
    else:
        raise AssertionError("Expected profile-name validation error")

    try:
        SystemProfile(
            name=" ",
            retrieval_strategy="dense",
            generation_strategy="llm",
            features=("dense",),
        )
    except ValueError as error:
        assert "name" in str(error)
    else:
        raise AssertionError("Expected profile validation error")
