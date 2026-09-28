from dataclasses import dataclass
from pathlib import Path

from app.db.qdrant import QdrantCollectionConfig
from app.ingestion.chunker import ChunkingConfig
from app.ingestion.indexer import (
    IndexingConfig,
    build_index,
    build_index_from_sources_csv,
)
from app.ingestion.models import LoadedDocumentPart, SourceRecord
from app.rag.embeddings import EmbeddedChunk


@dataclass(frozen=True)
class FakeCollectionDescription:
    name: str


@dataclass(frozen=True)
class FakeCollectionsResponse:
    collections: list[FakeCollectionDescription]


class FakeQdrantClient:
    def __init__(self, collections: list[str] | None = None) -> None:
        self.collections = set(collections or [])
        self.created: list[str] = []
        self.deleted: list[str] = []
        self.upserts: list[tuple[str, list]] = []

    def get_collections(self) -> FakeCollectionsResponse:
        return FakeCollectionsResponse(
            [
                FakeCollectionDescription(name=collection_name)
                for collection_name in sorted(self.collections)
            ]
        )

    def create_collection(self, *, collection_name: str, vectors_config) -> None:
        self.collections.add(collection_name)
        self.created.append(collection_name)

    def delete_collection(self, *, collection_name: str) -> None:
        self.collections.discard(collection_name)
        self.deleted.append(collection_name)

    def upsert(self, *, collection_name: str, points: list) -> None:
        self.upserts.append((collection_name, points))


class FakeEmbedder:
    @property
    def dimension(self) -> int:
        return 3

    def embed_chunks(self, chunks) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=chunk,
                vector=[float(index), float(index + 1), float(index + 2)],
            )
            for index, chunk in enumerate(chunks, start=1)
        ]


def source(document_id: str = "DOC_TEST") -> SourceRecord:
    return SourceRecord(
        document_id=document_id,
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


def part(document_id: str = "DOC_TEST") -> LoadedDocumentPart:
    return LoadedDocumentPart(
        document_id=document_id,
        title="Router Guide",
        filename=None,
        page=1,
        section="Setup",
        category="setup",
        product="Router X",
        version="v1",
        language="English",
        source_url="https://example.com/router",
        source_type="html",
        text="Setup\n\nConnect the WAN cable.\n\nRestart the router.",
    )


def test_build_index_runs_pipeline_and_upserts_points() -> None:
    client = FakeQdrantClient()
    config = IndexingConfig(
        collection=QdrantCollectionConfig(
            url="http://localhost:6333",
            collection_name="supportlens_chunks",
            vector_size=3,
        ),
        chunking=ChunkingConfig(target_tokens=50, overlap_blocks=0),
    )

    result = build_index(
        [source()],
        config=config,
        client=client,
        embedder=FakeEmbedder(),
        document_loader=lambda source_record, local_path: [part(source_record.document_id)],
    )

    assert client.created == ["supportlens_chunks"]
    assert len(client.upserts) == 1
    assert client.upserts[0][0] == "supportlens_chunks"
    assert client.upserts[0][1][0].payload["chunk_id"] == "DOC_TEST_C0001"
    assert result.documents_seen == 1
    assert result.documents_indexed == 1
    assert result.parts_count == 1
    assert result.chunks_count == 1
    assert result.points_upserted == 1


def test_build_index_batches_upserts() -> None:
    client = FakeQdrantClient()
    config = IndexingConfig(
        collection=QdrantCollectionConfig(
            url="http://localhost:6333",
            collection_name="supportlens_chunks",
            vector_size=3,
        ),
        chunking=ChunkingConfig(target_tokens=3, overlap_blocks=0),
        upsert_batch_size=1,
    )

    result = build_index(
        [source()],
        config=config,
        client=client,
        embedder=FakeEmbedder(),
        document_loader=lambda source_record, local_path: [part(source_record.document_id)],
    )

    assert result.points_upserted == 3
    assert len(client.upserts) == 3


def test_build_index_can_reset_collection_before_indexing() -> None:
    client = FakeQdrantClient(["supportlens_chunks"])
    config = IndexingConfig(
        collection=QdrantCollectionConfig(
            url="http://localhost:6333",
            collection_name="supportlens_chunks",
            vector_size=3,
        ),
        reset_collection=True,
    )

    build_index(
        [source()],
        config=config,
        client=client,
        embedder=FakeEmbedder(),
        document_loader=lambda source_record, local_path: [part(source_record.document_id)],
    )

    assert client.deleted == ["supportlens_chunks"]
    assert client.created == ["supportlens_chunks"]


def test_build_index_passes_resolved_local_paths_to_loader(tmp_path: Path) -> None:
    html_path = tmp_path / "router.html"
    html_path.write_text("<main>Router setup</main>", encoding="utf-8")
    seen_paths: list[Path | None] = []

    def document_loader(
        source_record: SourceRecord,
        local_path: Path | None,
    ) -> list[LoadedDocumentPart]:
        seen_paths.append(local_path)
        return [part(source_record.document_id)]

    build_index(
        [source()],
        config=IndexingConfig(
            collection=QdrantCollectionConfig(
                url="http://localhost:6333",
                collection_name="supportlens_chunks",
                vector_size=3,
            )
        ),
        client=FakeQdrantClient(),
        embedder=FakeEmbedder(),
        local_path_resolver=lambda source_record: html_path,
        document_loader=document_loader,
    )

    assert seen_paths == [html_path]


def test_build_index_from_sources_csv_reads_registry(tmp_path: Path) -> None:
    sources_csv = tmp_path / "sources.csv"
    sources_csv.write_text(
        "\n".join(
            [
                "document_id,title,category,source_url,product,version,language,retrieval_date,license,notes,source_type,raw_storage_policy",
                "DOC_TEST,Router Guide,setup,https://example.com/router,Router X,v1,English,2026-09-28,Test,Fixture,html,test_only",
            ]
        ),
        encoding="utf-8",
    )

    result = build_index_from_sources_csv(
        sources_csv,
        config=IndexingConfig(
            collection=QdrantCollectionConfig(
                url="http://localhost:6333",
                collection_name="supportlens_chunks",
                vector_size=3,
            )
        ),
        client=FakeQdrantClient(),
        embedder=FakeEmbedder(),
        document_loader=lambda source_record, local_path: [part(source_record.document_id)],
    )

    assert result.documents_seen == 1
    assert result.document_results[0].document_id == "DOC_TEST"


def test_indexing_config_rejects_invalid_batch_size() -> None:
    try:
        IndexingConfig(
            collection=QdrantCollectionConfig(
                url="http://localhost:6333",
                collection_name="supportlens_chunks",
            ),
            upsert_batch_size=0,
        )
    except ValueError as error:
        assert "upsert_batch_size" in str(error)
    else:
        raise AssertionError("Expected upsert_batch_size validation error")
