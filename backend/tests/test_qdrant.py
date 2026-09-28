from dataclasses import dataclass

from qdrant_client.models import Distance

from app.db.qdrant import (
    DEFAULT_VECTOR_SIZE,
    QdrantCollectionConfig,
    collection_exists,
    ensure_collection,
    qdrant_point_id,
    reset_collection,
    to_qdrant_point,
)
from app.ingestion.chunker import ChunkingConfig, chunk_blocks
from app.ingestion.structure import BlockType, StructuredBlock
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
        self.created: list[tuple[str, int, Distance]] = []
        self.deleted: list[str] = []

    def get_collections(self) -> FakeCollectionsResponse:
        return FakeCollectionsResponse(
            [
                FakeCollectionDescription(name=collection_name)
                for collection_name in sorted(self.collections)
            ]
        )

    def create_collection(self, *, collection_name: str, vectors_config) -> None:
        self.collections.add(collection_name)
        self.created.append(
            (collection_name, vectors_config.size, vectors_config.distance)
        )

    def delete_collection(self, *, collection_name: str) -> None:
        self.collections.discard(collection_name)
        self.deleted.append(collection_name)


def block(index: int, text: str) -> StructuredBlock:
    return StructuredBlock(
        block_id=f"DOC_TEST_B{index:04d}",
        block_type=BlockType.PARAGRAPH,
        text=text,
        section="Setup",
        page=1,
        document_id="DOC_TEST",
        title="Router Guide",
        category="setup",
        product="Router X",
        version="v1",
        language="English",
        source_url="https://example.com/router",
        source_type="html",
    )


def embedded_chunk(vector: list[float] | None = None) -> EmbeddedChunk:
    chunks = chunk_blocks(
        [block(1, "Factory Reset"), block(2, "Hold the reset button.")],
        ChunkingConfig(target_tokens=50, overlap_blocks=0),
    )
    return EmbeddedChunk(chunk=chunks[0], vector=vector or [0.1, 0.2, 0.3])


def test_collection_config_uses_expected_defaults() -> None:
    config = QdrantCollectionConfig(
        url="http://localhost:6333",
        collection_name="supportlens_chunks",
    )

    assert config.vector_size == DEFAULT_VECTOR_SIZE
    assert config.distance == Distance.COSINE


def test_ensure_collection_creates_missing_collection() -> None:
    client = FakeQdrantClient()
    config = QdrantCollectionConfig(
        url="http://localhost:6333",
        collection_name="supportlens_chunks",
        vector_size=384,
    )

    created = ensure_collection(client, config)

    assert created is True
    assert collection_exists(client, "supportlens_chunks") is True
    assert client.created == [("supportlens_chunks", 384, Distance.COSINE)]


def test_ensure_collection_does_not_recreate_existing_collection() -> None:
    client = FakeQdrantClient(["supportlens_chunks"])
    config = QdrantCollectionConfig(
        url="http://localhost:6333",
        collection_name="supportlens_chunks",
    )

    created = ensure_collection(client, config)

    assert created is False
    assert client.created == []


def test_reset_collection_deletes_existing_collection_before_create() -> None:
    client = FakeQdrantClient(["supportlens_chunks"])
    config = QdrantCollectionConfig(
        url="http://localhost:6333",
        collection_name="supportlens_chunks",
        vector_size=384,
    )

    reset_collection(client, config)

    assert client.deleted == ["supportlens_chunks"]
    assert client.created == [("supportlens_chunks", 384, Distance.COSINE)]


def test_to_qdrant_point_preserves_payload_and_uses_deterministic_uuid() -> None:
    embedded = embedded_chunk([0.1, 0.2, 0.3])

    point = to_qdrant_point(embedded, vector_size=3)

    assert point.id == qdrant_point_id("DOC_TEST_C0001")
    assert point.id != qdrant_point_id("DOC_TEST_C0002")
    assert point.vector == [0.1, 0.2, 0.3]
    assert point.payload["chunk_id"] == "DOC_TEST_C0001"
    assert point.payload["text"] == embedded.chunk.text


def test_to_qdrant_point_rejects_wrong_vector_size() -> None:
    try:
        to_qdrant_point(embedded_chunk([0.1, 0.2]), vector_size=3)
    except ValueError as error:
        assert "vector size mismatch" in str(error)
    else:
        raise AssertionError("Expected vector size validation error")
