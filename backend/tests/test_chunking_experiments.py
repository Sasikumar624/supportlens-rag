from dataclasses import dataclass

from app.db.qdrant import QdrantCollectionConfig
from app.evaluation.chunking_experiments import (
    ChunkingExperiment,
    default_chunking_experiments,
    run_chunking_experiments,
    select_best_experiment,
)
from app.evaluation.dataset import EvaluationQuestion, ExpectedEvidence, QuestionCategory
from app.evaluation.metrics import (
    RetrievalMetrics,
    QuestionRetrievalEvaluation,
)
from app.evaluation.retrieval_eval import RetrievalEvaluationReport
from app.ingestion.chunker import ChunkingConfig
from app.ingestion.indexer import (
    DocumentIndexingResult,
    IndexingConfig,
    IndexingResult,
)
from app.ingestion.models import SourceRecord
from app.rag.retriever import RetrievalResult


class FakeRetriever:
    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id

    def retrieve(self, query: str) -> list[RetrievalResult]:
        document_id = "DOC_GOOD" if self.experiment_id == "good" else "DOC_BAD"
        return [
            RetrievalResult(
                point_id=f"{document_id}_POINT",
                score=0.9,
                payload={
                    "document_id": document_id,
                    "chunk_id": f"{document_id}_C0001",
                    "text": "retrieved text",
                },
            )
        ]


def source() -> SourceRecord:
    return SourceRecord(
        document_id="DOC_GOOD",
        title="Router Guide",
        category="setup",
        source_url="https://example.com/router",
        product="Router X",
        version="v1",
        language="English",
        retrieval_date="2026-09-28",
        license="Test fixture",
        notes="Fixture source",
        source_type="html",
        raw_storage_policy="test_only",
    )


def question() -> EvaluationQuestion:
    return EvaluationQuestion(
        question_id="Q1",
        question="How do I set up the router?",
        category=QuestionCategory.SETUP,
        answerable=True,
        expected_evidence=[ExpectedEvidence(document_id="DOC_GOOD")],
    )


def indexing_result(chunks_count: int = 1) -> IndexingResult:
    return IndexingResult(
        collection_name="supportlens_chunks",
        documents_seen=1,
        documents_indexed=1,
        parts_count=1,
        blocks_count=2,
        chunks_count=chunks_count,
        points_upserted=chunks_count,
        document_results=[
            DocumentIndexingResult(
                document_id="DOC_GOOD",
                parts_count=1,
                blocks_count=2,
                chunks_count=chunks_count,
            )
        ],
    )


def base_config() -> IndexingConfig:
    return IndexingConfig(
        collection=QdrantCollectionConfig(
            url="http://localhost:6333",
            collection_name="supportlens_chunks",
            vector_size=3,
        ),
        chunking=ChunkingConfig(target_tokens=500, overlap_blocks=1),
    )


def test_default_chunking_experiments_cover_planned_variants() -> None:
    experiments = default_chunking_experiments()

    assert [experiment.chunking.target_tokens for experiment in experiments] == [
        300,
        500,
        800,
        500,
    ]
    assert [experiment.chunking.overlap_blocks for experiment in experiments] == [
        0,
        1,
        1,
        2,
    ]


def test_run_chunking_experiments_resets_and_applies_each_chunking_config() -> None:
    seen_configs: list[IndexingConfig] = []

    def fake_indexer(sources, *, config: IndexingConfig, **dependencies):
        seen_configs.append(config)
        return indexing_result()

    experiments = [
        ChunkingExperiment(
            experiment_id="good",
            description="Good chunking",
            chunking=ChunkingConfig(target_tokens=300, overlap_blocks=0),
        ),
        ChunkingExperiment(
            experiment_id="bad",
            description="Bad chunking",
            chunking=ChunkingConfig(target_tokens=800, overlap_blocks=1),
        ),
    ]

    results = run_chunking_experiments(
        sources=[source()],
        questions=[question()],
        base_indexing_config=base_config(),
        retriever_factory=lambda experiment: FakeRetriever(experiment.experiment_id),
        experiments=experiments,
        indexer=fake_indexer,
    )

    assert len(results) == 2
    assert all(config.reset_collection for config in seen_configs)
    assert seen_configs[0].chunking.target_tokens == 300
    assert seen_configs[1].chunking.target_tokens == 800
    assert results[0].metrics.recall_at_5 == 1.0
    assert results[1].metrics.recall_at_5 == 0.0


def test_select_best_experiment_prefers_recall_then_mrr_then_smaller_index() -> None:
    experiment_a = ChunkingExperiment(
        experiment_id="a",
        description="A",
        chunking=ChunkingConfig(target_tokens=300, overlap_blocks=0),
    )
    experiment_b = ChunkingExperiment(
        experiment_id="b",
        description="B",
        chunking=ChunkingConfig(target_tokens=500, overlap_blocks=1),
    )

    result_a = ChunkingExperimentResultForTest(
        experiment=experiment_a,
        recall_at_5=1.0,
        mrr=0.5,
        chunks_count=10,
    ).to_result()
    result_b = ChunkingExperimentResultForTest(
        experiment=experiment_b,
        recall_at_5=1.0,
        mrr=0.5,
        chunks_count=5,
    ).to_result()

    assert select_best_experiment([result_a, result_b]).experiment.experiment_id == "b"


def test_chunking_experiments_validate_non_empty_inputs() -> None:
    try:
        ChunkingExperiment(
            experiment_id=" ",
            description="Empty ID",
            chunking=ChunkingConfig(),
        )
    except ValueError as error:
        assert "experiment_id" in str(error)
    else:
        raise AssertionError("Expected experiment_id validation error")

    try:
        select_best_experiment([])
    except ValueError as error:
        assert "results" in str(error)
    else:
        raise AssertionError("Expected results validation error")


@dataclass(frozen=True)
class ChunkingExperimentResultForTest:
    experiment: ChunkingExperiment
    recall_at_5: float
    mrr: float
    chunks_count: int

    def to_result(self):
        from app.evaluation.chunking_experiments import ChunkingExperimentResult

        return ChunkingExperimentResult(
            experiment=self.experiment,
            indexing_result=indexing_result(self.chunks_count),
            retrieval_report=RetrievalEvaluationReport(
                metrics=RetrievalMetrics(
                    total_questions=1,
                    answerable_questions=1,
                    evaluated_questions=1,
                    hit_rate=self.recall_at_5,
                    recall_at_1=0.0,
                    recall_at_3=0.0,
                    recall_at_5=self.recall_at_5,
                    mrr=self.mrr,
                ),
                question_evaluations=[
                    QuestionRetrievalEvaluation(
                        question_id="Q1",
                        answerable=True,
                        expected_document_ids=["DOC_GOOD"],
                        retrieved_document_ids=["DOC_GOOD"],
                        first_relevant_rank=1,
                    )
                ],
            ),
        )
