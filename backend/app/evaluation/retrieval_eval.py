from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from app.evaluation.dataset import EvaluationQuestion
from app.evaluation.metrics import (
    QuestionRetrievalEvaluation,
    RetrievalMetrics,
    calculate_retrieval_metrics,
    evaluate_retrieval_results,
)
from app.rag.retriever import RetrievalResult


class Retriever(Protocol):
    def retrieve(self, query: str) -> list[RetrievalResult]:
        ...


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    metrics: RetrievalMetrics
    question_evaluations: list[QuestionRetrievalEvaluation]
    elapsed_seconds: float | None = None


@dataclass(frozen=True)
class RetrievalComparisonReport:
    baseline: RetrievalEvaluationReport
    candidate: RetrievalEvaluationReport


def run_retrieval_evaluation(
    questions: Sequence[EvaluationQuestion],
    retriever: Retriever,
) -> RetrievalEvaluationReport:
    if not questions:
        raise ValueError("questions cannot be empty")

    started_at = perf_counter()
    question_evaluations: list[QuestionRetrievalEvaluation] = []
    for question in questions:
        results = retriever.retrieve(question.question)
        question_evaluations.append(evaluate_retrieval_results(question, results))

    return RetrievalEvaluationReport(
        metrics=calculate_retrieval_metrics(question_evaluations),
        question_evaluations=question_evaluations,
        elapsed_seconds=perf_counter() - started_at,
    )


def compare_retrievers(
    questions: Sequence[EvaluationQuestion],
    *,
    baseline_retriever: Retriever,
    candidate_retriever: Retriever,
) -> RetrievalComparisonReport:
    return RetrievalComparisonReport(
        baseline=run_retrieval_evaluation(questions, baseline_retriever),
        candidate=run_retrieval_evaluation(questions, candidate_retriever),
    )
