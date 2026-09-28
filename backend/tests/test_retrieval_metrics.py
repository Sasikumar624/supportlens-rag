from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence, QuestionCategory
from app.evaluation.metrics import (
    calculate_retrieval_metrics,
    evaluate_retrieval_results,
)
from app.evaluation.retrieval_eval import run_retrieval_evaluation
from app.rag.retriever import RetrievalResult


class FakeRetriever:
    def __init__(self, results_by_query: dict[str, list[RetrievalResult]]) -> None:
        self.results_by_query = results_by_query

    def retrieve(self, query: str) -> list[RetrievalResult]:
        return self.results_by_query.get(query, [])


def question(
    question_id: str,
    text: str,
    expected_document_ids: list[str],
    *,
    answerable: bool = True,
) -> EvaluationQuestion:
    return EvaluationQuestion(
        question_id=question_id,
        question=text,
        category=QuestionCategory.TROUBLESHOOTING
        if answerable
        else QuestionCategory.UNANSWERABLE,
        answerable=answerable,
        expected_evidence=[
            ExpectedEvidence(document_id=document_id)
            for document_id in expected_document_ids
        ],
    )


def result(document_id: str, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        point_id=f"{document_id}_POINT",
        score=score,
        payload={
            "document_id": document_id,
            "chunk_id": f"{document_id}_C0001",
            "text": "Retrieved text",
        },
    )


def test_evaluate_retrieval_results_finds_first_relevant_rank() -> None:
    evaluation = evaluate_retrieval_results(
        question("Q1", "How do I reset OpenWrt?", ["DOC003"]),
        [result("DOC001"), result("DOC003"), result("DOC005")],
    )

    assert evaluation.hit is True
    assert evaluation.first_relevant_rank == 2
    assert evaluation.reciprocal_rank == 0.5


def test_calculate_retrieval_metrics_uses_answerable_questions_only() -> None:
    evaluations = [
        evaluate_retrieval_results(
            question("Q1", "setup", ["DOC001"]),
            [result("DOC001")],
        ),
        evaluate_retrieval_results(
            question("Q2", "reset", ["DOC003"]),
            [result("DOC001"), result("DOC002"), result("DOC003")],
        ),
        evaluate_retrieval_results(
            question("Q3", "missing", ["DOC005"]),
            [result("DOC001"), result("DOC002")],
        ),
        evaluate_retrieval_results(
            question("Q4", "sports", [], answerable=False),
            [],
        ),
    ]

    metrics = calculate_retrieval_metrics(evaluations)

    assert metrics.total_questions == 4
    assert metrics.answerable_questions == 3
    assert metrics.evaluated_questions == 3
    assert round(metrics.hit_rate, 4) == 0.6667
    assert round(metrics.recall_at_1, 4) == 0.3333
    assert round(metrics.recall_at_3, 4) == 0.6667
    assert round(metrics.recall_at_5, 4) == 0.6667
    assert round(metrics.mrr, 4) == 0.4444


def test_run_retrieval_evaluation_calls_retriever_for_each_question() -> None:
    questions = [
        question("Q1", "setup", ["DOC001"]),
        question("Q2", "reset", ["DOC003"]),
    ]
    retriever = FakeRetriever(
        {
            "setup": [result("DOC001")],
            "reset": [result("DOC001"), result("DOC003")],
        }
    )

    report = run_retrieval_evaluation(questions, retriever)

    assert len(report.question_evaluations) == 2
    assert report.question_evaluations[0].first_relevant_rank == 1
    assert report.question_evaluations[1].first_relevant_rank == 2
    assert report.metrics.recall_at_3 == 1.0


def test_retrieval_metrics_reject_empty_inputs() -> None:
    try:
        calculate_retrieval_metrics([])
    except ValueError as error:
        assert "evaluations" in str(error)
    else:
        raise AssertionError("Expected empty evaluations validation error")

    try:
        run_retrieval_evaluation([], FakeRetriever({}))
    except ValueError as error:
        assert "questions" in str(error)
    else:
        raise AssertionError("Expected empty questions validation error")
