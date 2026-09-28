from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence, QuestionCategory
from app.evaluation.generation import (
    calculate_generation_metrics,
    evaluate_generated_answer,
    run_generation_evaluation,
)
from app.rag.generator import GeneratedAnswer, SourceCitation
from app.rag.retriever import RetrievalResult


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
    *,
    answerable: bool = True,
    expected_document_ids: list[str] | None = None,
    required_terms: list[str] | None = None,
) -> EvaluationQuestion:
    expected_document_ids = expected_document_ids or []
    return EvaluationQuestion(
        question_id=question_id,
        question=text,
        category=QuestionCategory.TROUBLESHOOTING
        if answerable
        else QuestionCategory.OUT_OF_DOMAIN,
        answerable=answerable,
        expected_evidence=[
            ExpectedEvidence(
                document_id=document_id,
                required_terms=required_terms,
            )
            for document_id in expected_document_ids
        ],
    )


def result(document_id: str, text: str, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        point_id=f"{document_id}_POINT",
        score=score,
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


def generated(
    answer: str,
    context_chunks: list[RetrievalResult],
    sources: list[SourceCitation],
    *,
    refused: bool = False,
) -> GeneratedAnswer:
    return GeneratedAnswer(
        question="Question?",
        answer=answer,
        sources=sources,
        context_chunks=context_chunks,
        refused=refused,
        no_answer_reason="no_context" if refused else None,
    )


def test_evaluate_generated_answer_scores_grounded_cited_answer() -> None:
    evaluation = evaluate_generated_answer(
        question(
            "Q1",
            "How do I reset Router X?",
            expected_document_ids=["DOC_RESET"],
            required_terms=["reset button", "ten seconds"],
        ),
        generated(
            "Hold the reset button for ten seconds. [1]",
            [
                result(
                    "DOC_RESET",
                    "Hold the reset button for ten seconds.",
                )
            ],
            [source(1, "DOC_RESET")],
        ),
    )

    assert evaluation.context_precision == 1.0
    assert evaluation.context_recall == 1.0
    assert evaluation.no_answer_correctness == 1.0
    assert evaluation.citation_correctness == 1.0
    assert evaluation.answer_relevance == 1.0
    assert evaluation.faithfulness == 1.0
    assert evaluation.issues == []


def test_evaluate_generated_answer_flags_wrong_refusal_for_answerable_question() -> None:
    evaluation = evaluate_generated_answer(
        question("Q1", "How do I reset Router X?", expected_document_ids=["DOC_RESET"]),
        generated(
            "I could not find information relevant to that question.",
            [],
            [],
            refused=True,
        ),
    )

    assert evaluation.no_answer_correctness == 0.0
    assert evaluation.context_recall == 0.0
    assert "incorrect_no_answer_decision" in evaluation.issues
    assert "missing_expected_context" in evaluation.issues


def test_evaluate_generated_answer_scores_correct_no_answer() -> None:
    evaluation = evaluate_generated_answer(
        question("Q2", "Who won the football match?", answerable=False),
        generated(
            "I could not find information relevant to that question.",
            [],
            [],
            refused=True,
        ),
    )

    assert evaluation.no_answer_correctness == 1.0
    assert evaluation.answer_relevance == 1.0
    assert evaluation.context_precision == 1.0
    assert evaluation.context_recall == 1.0
    assert evaluation.citation_correctness == 1.0
    assert evaluation.issues == []


def test_evaluate_generated_answer_flags_invalid_or_irrelevant_citation() -> None:
    evaluation = evaluate_generated_answer(
        question("Q3", "How do I update firmware?", expected_document_ids=["DOC_FW"]),
        generated(
            "Download the firmware image first. [9]",
            [result("DOC_FW", "Download the firmware image first.")],
            [source(1, "DOC_FW")],
        ),
    )

    assert evaluation.cited_source_ids == [9]
    assert evaluation.citation_correctness == 0.0
    assert "incorrect_citations" in evaluation.issues


def test_calculate_generation_metrics_averages_question_scores() -> None:
    evaluations = [
        evaluate_generated_answer(
            question("Q1", "reset", expected_document_ids=["DOC_RESET"]),
            generated(
                "Hold the reset button. [1]",
                [result("DOC_RESET", "Hold the reset button.")],
                [source(1, "DOC_RESET")],
            ),
        ),
        evaluate_generated_answer(
            question("Q2", "sports", answerable=False),
            generated("The home team won. [1]", [result("DOC_SPORTS", "Sports")], []),
        ),
    ]

    metrics = calculate_generation_metrics(evaluations)

    assert metrics.total_questions == 2
    assert metrics.answerable_questions == 1
    assert metrics.unanswerable_questions == 1
    assert metrics.no_answer_accuracy == 0.5
    assert metrics.average_citation_correctness == 0.5
    assert 0.0 < metrics.average_overall_score < 1.0


def test_run_generation_evaluation_calls_pipeline_for_each_question() -> None:
    questions = [
        question("Q1", "reset", expected_document_ids=["DOC_RESET"]),
        question("Q2", "sports", answerable=False),
    ]
    pipeline = FakePipeline(
        {
            "reset": generated(
                "Hold the reset button. [1]",
                [result("DOC_RESET", "Hold the reset button.")],
                [source(1, "DOC_RESET")],
            ),
            "sports": generated(
                "I could not find information relevant to that question.",
                [],
                [],
                refused=True,
            ),
        }
    )

    report = run_generation_evaluation(questions, pipeline)

    assert pipeline.calls == ["reset", "sports"]
    assert len(report.question_evaluations) == 2
    assert report.metrics.no_answer_accuracy == 1.0
    assert report.elapsed_seconds is not None
    assert report.elapsed_seconds >= 0.0


def test_generation_metrics_reject_empty_inputs() -> None:
    try:
        calculate_generation_metrics([])
    except ValueError as error:
        assert "evaluations" in str(error)
    else:
        raise AssertionError("Expected empty evaluations validation error")

    try:
        run_generation_evaluation([], FakePipeline({}))
    except ValueError as error:
        assert "questions" in str(error)
    else:
        raise AssertionError("Expected empty questions validation error")
