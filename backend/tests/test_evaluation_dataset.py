import json
from pathlib import Path

from app.evaluation.dataset import (
    QuestionCategory,
    dataset_summary,
    load_evaluation_dataset,
    validate_evaluation_dataset,
)


def test_load_evaluation_dataset_validates_seed_dataset() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    questions = load_evaluation_dataset(repo_root / "evaluation" / "dataset.json")
    validate_evaluation_dataset(
        questions,
        sources_csv=repo_root / "data" / "sources.csv",
    )

    assert len(questions) >= 10
    assert any(question.answerable for question in questions)
    assert any(not question.answerable for question in questions)
    assert QuestionCategory.PROCEDURE in {question.category for question in questions}
    assert QuestionCategory.OUT_OF_DOMAIN in {question.category for question in questions}


def test_dataset_summary_counts_categories() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    questions = load_evaluation_dataset(repo_root / "evaluation" / "dataset.json")

    summary = dataset_summary(questions)

    assert summary["total"] == len(questions)
    assert summary["answerable_count"] + summary["unanswerable_count"] == len(questions)
    assert summary["troubleshooting"] >= 1


def test_evaluation_dataset_rejects_duplicate_ids(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "EVAL_DUP",
                    "question": "How do I set up OpenWrt?",
                    "category": "setup",
                    "answerable": True,
                    "expected_evidence": [{"document_id": "DOC001"}],
                },
                {
                    "question_id": "EVAL_DUP",
                    "question": "How do I reset OpenWrt?",
                    "category": "procedure",
                    "answerable": True,
                    "expected_evidence": [{"document_id": "DOC003"}],
                },
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_evaluation_dataset(dataset_path)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("Expected duplicate ID validation error")


def test_evaluation_dataset_rejects_answerable_question_without_evidence(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "EVAL_BAD",
                    "question": "How do I reset OpenWrt?",
                    "category": "procedure",
                    "answerable": True,
                    "expected_evidence": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_evaluation_dataset(dataset_path)
    except ValueError as error:
        assert "expected evidence" in str(error)
    else:
        raise AssertionError("Expected missing evidence validation error")
