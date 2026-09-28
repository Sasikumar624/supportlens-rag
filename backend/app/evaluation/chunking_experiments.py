from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.evaluation.dataset import EvaluationQuestion
from app.evaluation.metrics import RetrievalMetrics
from app.evaluation.retrieval_eval import RetrievalEvaluationReport, run_retrieval_evaluation
from app.ingestion.chunker import ChunkingConfig
from app.ingestion.indexer import IndexingConfig, IndexingResult, build_index
from app.ingestion.models import SourceRecord
from app.rag.retriever import RetrievalResult


@dataclass(frozen=True)
class ChunkingExperiment:
    experiment_id: str
    description: str
    chunking: ChunkingConfig

    def __post_init__(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id cannot be empty")
        if not self.description.strip():
            raise ValueError("description cannot be empty")


@dataclass(frozen=True)
class ChunkingExperimentResult:
    experiment: ChunkingExperiment
    indexing_result: IndexingResult
    retrieval_report: RetrievalEvaluationReport

    @property
    def metrics(self) -> RetrievalMetrics:
        return self.retrieval_report.metrics


class ExperimentRetriever(Protocol):
    def retrieve(self, query: str) -> list[RetrievalResult]:
        ...


RetrieverFactory = Callable[[ChunkingExperiment], ExperimentRetriever]


def default_chunking_experiments() -> list[ChunkingExperiment]:
    return [
        ChunkingExperiment(
            experiment_id="chunk_300_overlap_0",
            description="Structure-aware chunks targeting 300 tokens with no block overlap.",
            chunking=ChunkingConfig(target_tokens=300, overlap_blocks=0),
        ),
        ChunkingExperiment(
            experiment_id="chunk_500_overlap_1",
            description="Structure-aware chunks targeting 500 tokens with one overlap block.",
            chunking=ChunkingConfig(target_tokens=500, overlap_blocks=1),
        ),
        ChunkingExperiment(
            experiment_id="chunk_800_overlap_1",
            description="Structure-aware chunks targeting 800 tokens with one overlap block.",
            chunking=ChunkingConfig(target_tokens=800, overlap_blocks=1),
        ),
        ChunkingExperiment(
            experiment_id="chunk_500_overlap_2",
            description="Structure-aware chunks targeting 500 tokens with two overlap blocks.",
            chunking=ChunkingConfig(target_tokens=500, overlap_blocks=2),
        ),
    ]


def run_chunking_experiments(
    *,
    sources: Sequence[SourceRecord],
    questions: Sequence[EvaluationQuestion],
    base_indexing_config: IndexingConfig,
    retriever_factory: RetrieverFactory,
    experiments: Sequence[ChunkingExperiment] | None = None,
    indexer: Callable[..., IndexingResult] = build_index,
    **indexer_dependencies,
) -> list[ChunkingExperimentResult]:
    experiments = list(experiments or default_chunking_experiments())
    if not experiments:
        raise ValueError("experiments cannot be empty")

    results: list[ChunkingExperimentResult] = []
    for experiment in experiments:
        indexing_config = IndexingConfig(
            collection=base_indexing_config.collection,
            chunking=experiment.chunking,
            reset_collection=True,
            upsert_batch_size=base_indexing_config.upsert_batch_size,
        )
        indexing_result = indexer(
            sources,
            config=indexing_config,
            **indexer_dependencies,
        )
        retrieval_report = run_retrieval_evaluation(
            questions,
            retriever_factory(experiment),
        )
        results.append(
            ChunkingExperimentResult(
                experiment=experiment,
                indexing_result=indexing_result,
                retrieval_report=retrieval_report,
            )
        )

    return results


def select_best_experiment(
    results: Sequence[ChunkingExperimentResult],
) -> ChunkingExperimentResult:
    if not results:
        raise ValueError("results cannot be empty")

    return max(
        results,
        key=lambda result: (
            result.metrics.recall_at_5,
            result.metrics.mrr,
            result.metrics.recall_at_3,
            -result.indexing_result.chunks_count,
        ),
    )
