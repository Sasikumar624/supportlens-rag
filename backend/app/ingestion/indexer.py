from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from qdrant_client.models import PointStruct

from app.core.logging import get_logger
from app.db.qdrant import (
    QdrantCollectionConfig,
    ensure_collection,
    get_qdrant_client,
    reset_collection,
    to_qdrant_points,
)
from app.ingestion.chunker import Chunk, ChunkingConfig, chunk_blocks
from app.ingestion.loaders import load_document, load_sources_csv
from app.ingestion.models import LoadedDocumentPart, SourceRecord
from app.ingestion.structure import StructuredBlock, detect_structure
from app.rag.embeddings import EmbeddedChunk, EmbeddingModel


logger = get_logger(__name__)


class Embedder(Protocol):
    @property
    def dimension(self) -> int | None:
        ...

    def embed_chunks(self, chunks: Sequence[Chunk]) -> list[EmbeddedChunk]:
        ...


class QdrantWriter(Protocol):
    def upsert(
        self,
        *,
        collection_name: str,
        points: list[PointStruct],
    ):
        ...


DocumentLoader = Callable[[SourceRecord, Path | None], list[LoadedDocumentPart]]
LocalPathResolver = Callable[[SourceRecord], Path | None]


@dataclass(frozen=True)
class IndexingConfig:
    collection: QdrantCollectionConfig
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    reset_collection: bool = False
    upsert_batch_size: int = 64

    def __post_init__(self) -> None:
        if self.upsert_batch_size <= 0:
            raise ValueError("upsert_batch_size must be positive")


@dataclass(frozen=True)
class DocumentIndexingResult:
    document_id: str
    parts_count: int
    blocks_count: int
    chunks_count: int


@dataclass(frozen=True)
class IndexingResult:
    collection_name: str
    documents_seen: int
    documents_indexed: int
    parts_count: int
    blocks_count: int
    chunks_count: int
    points_upserted: int
    document_results: list[DocumentIndexingResult]


def build_index_from_sources_csv(
    sources_csv: Path,
    *,
    config: IndexingConfig | None = None,
    client: QdrantWriter | None = None,
    embedder: Embedder | None = None,
    local_path_resolver: LocalPathResolver | None = None,
    document_loader: DocumentLoader | None = None,
) -> IndexingResult:
    sources = load_sources_csv(sources_csv)
    return build_index(
        sources,
        config=config,
        client=client,
        embedder=embedder,
        local_path_resolver=local_path_resolver,
        document_loader=document_loader,
    )


def build_index(
    sources: Sequence[SourceRecord],
    *,
    config: IndexingConfig | None = None,
    client: QdrantWriter | None = None,
    embedder: Embedder | None = None,
    local_path_resolver: LocalPathResolver | None = None,
    document_loader: DocumentLoader | None = None,
) -> IndexingResult:
    embedder = embedder or EmbeddingModel.from_settings()
    collection = _resolve_collection_config(config, embedder)
    config = config or IndexingConfig(collection=collection)
    client = client or get_qdrant_client(collection)
    document_loader = document_loader or _load_document_for_indexing

    if config.reset_collection:
        logger.info("Resetting Qdrant collection %s", collection.collection_name)
        reset_collection(client, collection)
    else:
        created = ensure_collection(client, collection)
        if created:
            logger.info("Created Qdrant collection %s", collection.collection_name)
        else:
            logger.info("Using existing Qdrant collection %s", collection.collection_name)

    document_results: list[DocumentIndexingResult] = []
    all_embedded_chunks: list[EmbeddedChunk] = []

    for source in sources:
        logger.info("Indexing document %s", source.document_id)
        local_path = local_path_resolver(source) if local_path_resolver else None
        parts = document_loader(source, local_path)
        blocks = _detect_all_blocks(parts)
        chunks = chunk_blocks(blocks, config.chunking)
        embedded_chunks = embedder.embed_chunks(chunks)
        logger.info(
            "Prepared document %s: %s parts, %s blocks, %s chunks",
            source.document_id,
            len(parts),
            len(blocks),
            len(chunks),
        )

        all_embedded_chunks.extend(embedded_chunks)
        document_results.append(
            DocumentIndexingResult(
                document_id=source.document_id,
                parts_count=len(parts),
                blocks_count=len(blocks),
                chunks_count=len(chunks),
            )
        )

    points = to_qdrant_points(
        all_embedded_chunks,
        vector_size=collection.vector_size,
    )
    _upsert_in_batches(
        client,
        collection_name=collection.collection_name,
        points=points,
        batch_size=config.upsert_batch_size,
    )

    indexed_documents = [
        result for result in document_results if result.chunks_count > 0
    ]
    result = IndexingResult(
        collection_name=collection.collection_name,
        documents_seen=len(sources),
        documents_indexed=len(indexed_documents),
        parts_count=sum(result.parts_count for result in document_results),
        blocks_count=sum(result.blocks_count for result in document_results),
        chunks_count=sum(result.chunks_count for result in document_results),
        points_upserted=len(points),
        document_results=document_results,
    )
    logger.info(
        "Indexed %s documents into %s with %s points",
        len(indexed_documents),
        collection.collection_name,
        len(points),
    )
    return result


def _resolve_collection_config(
    config: IndexingConfig | None,
    embedder: Embedder,
) -> QdrantCollectionConfig:
    if config is not None:
        return config.collection

    dimension = embedder.dimension
    if dimension is None:
        return QdrantCollectionConfig.from_settings()

    return QdrantCollectionConfig.from_settings(vector_size=dimension)


def _detect_all_blocks(parts: Sequence[LoadedDocumentPart]) -> list[StructuredBlock]:
    blocks: list[StructuredBlock] = []
    for part in parts:
        blocks.extend(detect_structure(part))
    return blocks


def _upsert_in_batches(
    client: QdrantWriter,
    *,
    collection_name: str,
    points: list[PointStruct],
    batch_size: int,
) -> None:
    for index in range(0, len(points), batch_size):
        batch = points[index : index + batch_size]
        if not batch:
            continue
        logger.info(
            "Upserting %s points into Qdrant collection %s",
            len(batch),
            collection_name,
        )
        client.upsert(collection_name=collection_name, points=batch)


def _load_document_for_indexing(
    source: SourceRecord,
    local_path: Path | None,
) -> list[LoadedDocumentPart]:
    return load_document(source, local_path=local_path)
