import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.ingestion.loaders import load_sources_csv


class QuestionCategory(StrEnum):
    SIMPLE_FACTUAL = "simple_factual"
    SETUP = "setup"
    TROUBLESHOOTING = "troubleshooting"
    PROCEDURE = "procedure"
    CONFIGURATION = "configuration"
    EXACT_TERM = "exact_term"
    MULTI_CHUNK = "multi_chunk"
    MULTI_DOCUMENT = "multi_document"
    UNANSWERABLE = "unanswerable"
    OUT_OF_DOMAIN = "out_of_domain"


@dataclass(frozen=True)
class ExpectedEvidence:
    document_id: str
    section: str | None = None
    required_terms: list[str] | None = None


@dataclass(frozen=True)
class EvaluationQuestion:
    question_id: str
    question: str
    category: QuestionCategory
    answerable: bool
    expected_evidence: list[ExpectedEvidence]
    notes: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "EvaluationQuestion":
        expected_evidence = [
            ExpectedEvidence(
                document_id=evidence["document_id"],
                section=evidence.get("section"),
                required_terms=evidence.get("required_terms"),
            )
            for evidence in row.get("expected_evidence", [])
        ]
        question = cls(
            question_id=row["question_id"],
            question=row["question"],
            category=QuestionCategory(row["category"]),
            answerable=bool(row["answerable"]),
            expected_evidence=expected_evidence,
            notes=row.get("notes"),
        )
        question.validate()
        return question

    def validate(self) -> None:
        if not self.question_id.strip():
            raise ValueError("question_id cannot be empty")
        if not self.question.strip():
            raise ValueError(f"{self.question_id}: question cannot be empty")
        if self.answerable and not self.expected_evidence:
            raise ValueError(
                f"{self.question_id}: answerable questions require expected evidence"
            )
        if not self.answerable and self.expected_evidence:
            raise ValueError(
                f"{self.question_id}: unanswerable questions cannot have expected evidence"
            )


def load_evaluation_dataset(path: Path) -> list[EvaluationQuestion]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("evaluation dataset must be a JSON list")

    questions = [EvaluationQuestion.from_dict(row) for row in rows]
    validate_evaluation_dataset(questions)
    return questions


def validate_evaluation_dataset(
    questions: list[EvaluationQuestion],
    *,
    sources_csv: Path | None = None,
) -> None:
    if not questions:
        raise ValueError("evaluation dataset cannot be empty")

    question_ids = [question.question_id for question in questions]
    duplicate_ids = sorted(
        question_id for question_id in set(question_ids) if question_ids.count(question_id) > 1
    )
    if duplicate_ids:
        raise ValueError(f"duplicate evaluation question IDs: {', '.join(duplicate_ids)}")

    for question in questions:
        question.validate()

    if sources_csv is not None:
        source_ids = {source.document_id for source in load_sources_csv(sources_csv)}
        for question in questions:
            for evidence in question.expected_evidence:
                if evidence.document_id not in source_ids:
                    raise ValueError(
                        f"{question.question_id}: unknown expected document "
                        f"{evidence.document_id}"
                    )


def dataset_summary(questions: list[EvaluationQuestion]) -> dict[str, int]:
    summary = {
        "total": len(questions),
        "answerable_count": sum(1 for question in questions if question.answerable),
        "unanswerable_count": sum(1 for question in questions if not question.answerable),
    }
    for category in QuestionCategory:
        summary[category.value] = sum(
            1 for question in questions if question.category == category
        )
    return summary
