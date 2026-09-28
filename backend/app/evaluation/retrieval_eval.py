from collections.abc import Sequence
from dataclasses import dataclass
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


def run_retrieval_evaluation(
    questions: Sequence[EvaluationQuestion],
    retriever: Retriever,
) -> RetrievalEvaluationReport:
    if not questions:
        raise ValueError("questions cannot be empty")

    question_evaluations: list[QuestionRetrievalEvaluation] = []
    for question in questions:
        results = retriever.retrieve(question.question)
        question_evaluations.append(evaluate_retrieval_results(question, results))

    return RetrievalEvaluationReport(
        metrics=calculate_retrieval_metrics(question_evaluations),
        question_evaluations=question_evaluations,
    )
