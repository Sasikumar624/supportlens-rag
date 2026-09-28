from collections.abc import Sequence
from dataclasses import dataclass, fields

from app.evaluation.dataset import EvaluationQuestion
from app.evaluation.generation import (
    AnsweringPipeline,
    GenerationEvaluationReport,
    run_generation_evaluation,
)
from app.evaluation.retrieval_eval import (
    RetrievalEvaluationReport,
    Retriever,
    run_retrieval_evaluation,
)


@dataclass(frozen=True)
class SystemProfile:
    name: str
    retrieval_strategy: str
    generation_strategy: str
    features: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if not self.retrieval_strategy.strip():
            raise ValueError("retrieval_strategy cannot be empty")
        if not self.generation_strategy.strip():
            raise ValueError("generation_strategy cannot be empty")
        if not self.features:
            raise ValueError("features cannot be empty")
        if any(not feature.strip() for feature in self.features):
            raise ValueError("features cannot contain empty values")


@dataclass(frozen=True)
class SystemUnderEvaluation:
    profile: SystemProfile
    retriever: Retriever
    pipeline: AnsweringPipeline


@dataclass(frozen=True)
class MetricDelta:
    metric_name: str
    baseline_value: float
    improved_value: float

    @property
    def absolute_delta(self) -> float:
        return self.improved_value - self.baseline_value


@dataclass(frozen=True)
class SystemEvaluationReport:
    profile: SystemProfile
    retrieval: RetrievalEvaluationReport
    generation: GenerationEvaluationReport


@dataclass(frozen=True)
class SystemComparisonReport:
    baseline: SystemEvaluationReport
    improved: SystemEvaluationReport
    retrieval_deltas: list[MetricDelta]
    generation_deltas: list[MetricDelta]


BASELINE_PROFILE = SystemProfile(
    name="baseline",
    retrieval_strategy="dense_top_5",
    generation_strategy="llm",
    features=(
        "basic_chunking",
        "dense_retrieval",
        "top_5_context",
        "llm_generation",
    ),
)


IMPROVED_PROFILE = SystemProfile(
    name="improved",
    retrieval_strategy="query_processed_hybrid_reranked",
    generation_strategy="grounded_llm_with_no_answer_and_citations",
    features=(
        "structure_aware_chunking",
        "metadata_filtering",
        "dense_retrieval",
        "keyword_sparse_retrieval",
        "hybrid_fusion",
        "reranking",
        "grounded_prompt",
        "no_answer_handling",
        "citations",
    ),
)


def compare_systems(
    questions: Sequence[EvaluationQuestion],
    *,
    baseline: SystemUnderEvaluation,
    improved: SystemUnderEvaluation,
) -> SystemComparisonReport:
    if not questions:
        raise ValueError("questions cannot be empty")
    if baseline.profile.name == improved.profile.name:
        raise ValueError("system profile names must be different")

    baseline_report = _evaluate_system(questions, baseline)
    improved_report = _evaluate_system(questions, improved)
    return SystemComparisonReport(
        baseline=baseline_report,
        improved=improved_report,
        retrieval_deltas=_metric_deltas(
            baseline_report.retrieval.metrics,
            improved_report.retrieval.metrics,
        ),
        generation_deltas=_metric_deltas(
            baseline_report.generation.metrics,
            improved_report.generation.metrics,
        ),
    )


def _evaluate_system(
    questions: Sequence[EvaluationQuestion],
    system: SystemUnderEvaluation,
) -> SystemEvaluationReport:
    return SystemEvaluationReport(
        profile=system.profile,
        retrieval=run_retrieval_evaluation(questions, system.retriever),
        generation=run_generation_evaluation(questions, system.pipeline),
    )


def _metric_deltas(baseline_metrics, improved_metrics) -> list[MetricDelta]:
    deltas: list[MetricDelta] = []
    for field in fields(baseline_metrics):
        baseline_value = getattr(baseline_metrics, field.name)
        improved_value = getattr(improved_metrics, field.name)
        if not isinstance(baseline_value, int | float):
            continue
        if not isinstance(improved_value, int | float):
            continue
        deltas.append(
            MetricDelta(
                metric_name=field.name,
                baseline_value=float(baseline_value),
                improved_value=float(improved_value),
            )
        )
    return deltas
