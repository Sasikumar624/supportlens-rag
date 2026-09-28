import re
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence
from app.rag.generator import GeneratedAnswer


class AnsweringPipeline(Protocol):
    def answer(self, question: str) -> GeneratedAnswer:
        ...


@dataclass(frozen=True)
class QuestionGenerationEvaluation:
    question_id: str
    answerable: bool
    refused: bool
    expected_document_ids: list[str]
    context_document_ids: list[str]
    cited_source_ids: list[int]
    faithfulness: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    no_answer_correctness: float
    citation_correctness: float
    issues: list[str]

    @property
    def overall_score(self) -> float:
        return _mean(
            [
                self.faithfulness,
                self.answer_relevance,
                self.context_precision,
                self.context_recall,
                self.no_answer_correctness,
                self.citation_correctness,
            ]
        )


@dataclass(frozen=True)
class GenerationMetrics:
    total_questions: int
    answerable_questions: int
    unanswerable_questions: int
    average_faithfulness: float
    average_answer_relevance: float
    average_context_precision: float
    average_context_recall: float
    no_answer_accuracy: float
    average_citation_correctness: float
    average_overall_score: float


@dataclass(frozen=True)
class GenerationEvaluationReport:
    metrics: GenerationMetrics
    question_evaluations: list[QuestionGenerationEvaluation]
    elapsed_seconds: float | None = None


def evaluate_generated_answer(
    question: EvaluationQuestion,
    generated_answer: GeneratedAnswer,
) -> QuestionGenerationEvaluation:
    expected_document_ids = _expected_document_ids(question.expected_evidence)
    context_document_ids = [
        result.document_id
        for result in generated_answer.context_chunks
        if result.document_id is not None
    ]
    cited_source_ids = _extract_cited_source_ids(generated_answer.answer)

    faithfulness = _faithfulness_score(generated_answer)
    answer_relevance = _answer_relevance_score(question, generated_answer)
    context_precision = _context_precision_score(
        question.answerable,
        expected_document_ids,
        context_document_ids,
    )
    context_recall = _context_recall_score(
        question.answerable,
        expected_document_ids,
        context_document_ids,
    )
    no_answer_correctness = _no_answer_correctness_score(
        question.answerable,
        generated_answer.refused,
    )
    citation_correctness = _citation_correctness_score(
        question.answerable,
        expected_document_ids,
        generated_answer,
        cited_source_ids,
    )
    issues = _generation_issues(
        question.answerable,
        generated_answer,
        no_answer_correctness,
        citation_correctness,
        context_recall,
    )

    return QuestionGenerationEvaluation(
        question_id=question.question_id,
        answerable=question.answerable,
        refused=generated_answer.refused,
        expected_document_ids=expected_document_ids,
        context_document_ids=context_document_ids,
        cited_source_ids=cited_source_ids,
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        context_precision=context_precision,
        context_recall=context_recall,
        no_answer_correctness=no_answer_correctness,
        citation_correctness=citation_correctness,
        issues=issues,
    )


def calculate_generation_metrics(
    evaluations: Sequence[QuestionGenerationEvaluation],
) -> GenerationMetrics:
    if not evaluations:
        raise ValueError("evaluations cannot be empty")

    answerable = [evaluation for evaluation in evaluations if evaluation.answerable]
    unanswerable = [
        evaluation for evaluation in evaluations if not evaluation.answerable
    ]

    return GenerationMetrics(
        total_questions=len(evaluations),
        answerable_questions=len(answerable),
        unanswerable_questions=len(unanswerable),
        average_faithfulness=_mean(
            evaluation.faithfulness for evaluation in evaluations
        ),
        average_answer_relevance=_mean(
            evaluation.answer_relevance for evaluation in evaluations
        ),
        average_context_precision=_mean(
            evaluation.context_precision for evaluation in evaluations
        ),
        average_context_recall=_mean(
            evaluation.context_recall for evaluation in evaluations
        ),
        no_answer_accuracy=_mean(
            evaluation.no_answer_correctness for evaluation in evaluations
        ),
        average_citation_correctness=_mean(
            evaluation.citation_correctness for evaluation in evaluations
        ),
        average_overall_score=_mean(
            evaluation.overall_score for evaluation in evaluations
        ),
    )


def run_generation_evaluation(
    questions: Sequence[EvaluationQuestion],
    pipeline: AnsweringPipeline,
) -> GenerationEvaluationReport:
    if not questions:
        raise ValueError("questions cannot be empty")

    started_at = perf_counter()
    question_evaluations = [
        evaluate_generated_answer(question, pipeline.answer(question.question))
        for question in questions
    ]
    return GenerationEvaluationReport(
        metrics=calculate_generation_metrics(question_evaluations),
        question_evaluations=question_evaluations,
        elapsed_seconds=perf_counter() - started_at,
    )


def _faithfulness_score(generated_answer: GeneratedAnswer) -> float:
    if generated_answer.refused:
        return 1.0

    answer_tokens = _content_tokens(_strip_citations(generated_answer.answer))
    if not answer_tokens:
        return 0.0

    context_text = " ".join(chunk.text for chunk in generated_answer.context_chunks)
    context_tokens = set(_content_tokens(context_text))
    if not context_tokens:
        return 0.0

    supported_tokens = [token for token in answer_tokens if token in context_tokens]
    return len(supported_tokens) / len(answer_tokens)


def _answer_relevance_score(
    question: EvaluationQuestion,
    generated_answer: GeneratedAnswer,
) -> float:
    if not question.answerable:
        return 1.0 if generated_answer.refused else 0.0
    if generated_answer.refused:
        return 0.0

    required_terms = _required_terms(question.expected_evidence)
    if not required_terms:
        return 1.0 if generated_answer.answer.strip() else 0.0

    normalized_answer = _normalize_text(generated_answer.answer)
    matched_terms = [
        term for term in required_terms if _normalize_text(term) in normalized_answer
    ]
    return len(matched_terms) / len(required_terms)


def _context_precision_score(
    answerable: bool,
    expected_document_ids: Sequence[str],
    context_document_ids: Sequence[str],
) -> float:
    if not context_document_ids:
        return 1.0 if not answerable else 0.0
    if not answerable:
        return 0.0

    expected = set(expected_document_ids)
    relevant_count = sum(
        1 for document_id in context_document_ids if document_id in expected
    )
    return relevant_count / len(context_document_ids)


def _context_recall_score(
    answerable: bool,
    expected_document_ids: Sequence[str],
    context_document_ids: Sequence[str],
) -> float:
    if not answerable:
        return 1.0
    if not expected_document_ids:
        return 0.0

    found = set(context_document_ids)
    expected = set(expected_document_ids)
    return len(expected.intersection(found)) / len(expected)


def _no_answer_correctness_score(answerable: bool, refused: bool) -> float:
    return 1.0 if refused != answerable else 0.0


def _citation_correctness_score(
    answerable: bool,
    expected_document_ids: Sequence[str],
    generated_answer: GeneratedAnswer,
    cited_source_ids: Sequence[int],
) -> float:
    source_ids = {source.source_id for source in generated_answer.sources}
    citations_are_valid = all(source_id in source_ids for source_id in cited_source_ids)

    if not answerable:
        return (
            1.0
            if generated_answer.refused
            and not generated_answer.sources
            and not cited_source_ids
            else 0.0
        )
    if generated_answer.refused or not cited_source_ids or not citations_are_valid:
        return 0.0

    expected = set(expected_document_ids)
    cited_documents = {
        source.document_id
        for source in generated_answer.sources
        if source.source_id in cited_source_ids and source.document_id is not None
    }
    return 1.0 if expected.intersection(cited_documents) else 0.0


def _generation_issues(
    answerable: bool,
    generated_answer: GeneratedAnswer,
    no_answer_correctness: float,
    citation_correctness: float,
    context_recall: float,
) -> list[str]:
    issues: list[str] = []
    if no_answer_correctness < 1.0:
        issues.append("incorrect_no_answer_decision")
    if answerable and context_recall < 1.0:
        issues.append("missing_expected_context")
    if citation_correctness < 1.0:
        issues.append("incorrect_citations")
    if answerable and not generated_answer.answer.strip():
        issues.append("empty_answer")
    return issues


def _extract_cited_source_ids(answer: str) -> list[int]:
    seen: set[int] = set()
    source_ids: list[int] = []
    for match in re.finditer(r"\[(\d+)\]", answer):
        source_id = int(match.group(1))
        if source_id in seen:
            continue
        seen.add(source_id)
        source_ids.append(source_id)
    return source_ids


def _expected_document_ids(expected_evidence: Sequence[ExpectedEvidence]) -> list[str]:
    seen: set[str] = set()
    document_ids: list[str] = []
    for evidence in expected_evidence:
        if evidence.document_id in seen:
            continue
        seen.add(evidence.document_id)
        document_ids.append(evidence.document_id)
    return document_ids


def _required_terms(expected_evidence: Sequence[ExpectedEvidence]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for evidence in expected_evidence:
        for term in evidence.required_terms or []:
            normalized = _normalize_text(term)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            terms.append(term)
    return terms


def _strip_citations(text: str) -> str:
    return re.sub(r"\[\d+\]", "", text)


def _content_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS and len(token) > 2
    ]


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)


_STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "how",
    "the",
    "that",
    "this",
    "to",
    "with",
    "you",
    "your",
}
