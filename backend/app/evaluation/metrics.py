from collections.abc import Sequence
from dataclasses import dataclass

from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence
from app.rag.retriever import RetrievalResult


@dataclass(frozen=True)
class QuestionRetrievalEvaluation:
    question_id: str
    answerable: bool
    expected_document_ids: list[str]
    retrieved_document_ids: list[str]
    first_relevant_rank: int | None

    @property
    def hit(self) -> bool:
        return self.first_relevant_rank is not None

    @property
    def reciprocal_rank(self) -> float:
        if self.first_relevant_rank is None:
            return 0.0
        return 1.0 / self.first_relevant_rank


@dataclass(frozen=True)
class RetrievalMetrics:
    total_questions: int
    answerable_questions: int
    evaluated_questions: int
    hit_rate: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float


def evaluate_retrieval_results(
    question: EvaluationQuestion,
    results: Sequence[RetrievalResult],
) -> QuestionRetrievalEvaluation:
    expected_document_ids = _expected_document_ids(question.expected_evidence)
    retrieved_document_ids = [
        result.document_id for result in results if result.document_id is not None
    ]
    first_relevant_rank = _first_relevant_rank(
        expected_document_ids,
        retrieved_document_ids,
    )
    return QuestionRetrievalEvaluation(
        question_id=question.question_id,
        answerable=question.answerable,
        expected_document_ids=expected_document_ids,
        retrieved_document_ids=retrieved_document_ids,
        first_relevant_rank=first_relevant_rank,
    )


def calculate_retrieval_metrics(
    evaluations: Sequence[QuestionRetrievalEvaluation],
) -> RetrievalMetrics:
    if not evaluations:
        raise ValueError("evaluations cannot be empty")

    answerable = [evaluation for evaluation in evaluations if evaluation.answerable]
    if not answerable:
        raise ValueError("at least one answerable evaluation is required")

    return RetrievalMetrics(
        total_questions=len(evaluations),
        answerable_questions=len(answerable),
        evaluated_questions=len(answerable),
        hit_rate=_mean(1.0 if evaluation.hit else 0.0 for evaluation in answerable),
        recall_at_1=_recall_at_k(answerable, 1),
        recall_at_3=_recall_at_k(answerable, 3),
        recall_at_5=_recall_at_k(answerable, 5),
        mrr=_mean(evaluation.reciprocal_rank for evaluation in answerable),
    )


def _expected_document_ids(expected_evidence: Sequence[ExpectedEvidence]) -> list[str]:
    seen: set[str] = set()
    document_ids: list[str] = []
    for evidence in expected_evidence:
        if evidence.document_id in seen:
            continue
        seen.add(evidence.document_id)
        document_ids.append(evidence.document_id)
    return document_ids


def _first_relevant_rank(
    expected_document_ids: Sequence[str],
    retrieved_document_ids: Sequence[str],
) -> int | None:
    expected = set(expected_document_ids)
    if not expected:
        return None

    for index, document_id in enumerate(retrieved_document_ids, start=1):
        if document_id in expected:
            return index
    return None


def _recall_at_k(
    evaluations: Sequence[QuestionRetrievalEvaluation],
    k: int,
) -> float:
    return _mean(
        1.0
        if evaluation.first_relevant_rank is not None
        and evaluation.first_relevant_rank <= k
        else 0.0
        for evaluation in evaluations
    )


def _mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)
