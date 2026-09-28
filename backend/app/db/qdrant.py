from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings, get_settings
from app.rag.embeddings import EmbeddedChunk


DEFAULT_VECTOR_SIZE = 384
DEFAULT_DISTANCE = Distance.COSINE


@dataclass(frozen=True)
class QdrantCollectionConfig:
    url: str
    collection_name: str
    vector_size: int = DEFAULT_VECTOR_SIZE
    distance: Distance = DEFAULT_DISTANCE
    api_key: str | None = None

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        vector_size: int = DEFAULT_VECTOR_SIZE,
    ) -> "QdrantCollectionConfig":
        settings = settings or get_settings()
        return cls(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection,
            vector_size=vector_size,
        )

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("url cannot be empty")
        if not self.collection_name.strip():
            raise ValueError("collection_name cannot be empty")
        if self.vector_size <= 0:
            raise ValueError("vector_size must be positive")


def get_qdrant_client(
    config: QdrantCollectionConfig | None = None,
) -> QdrantClient:
    config = config or QdrantCollectionConfig.from_settings()
    return QdrantClient(url=config.url, api_key=config.api_key)


def collection_exists(
    client: QdrantClient,
    collection_name: str,
) -> bool:
    collections = client.get_collections().collections
    return any(collection.name == collection_name for collection in collections)


def ensure_collection(
    client: QdrantClient,
    config: QdrantCollectionConfig,
) -> bool:
    if collection_exists(client, config.collection_name):
        return False

    client.create_collection(
        collection_name=config.collection_name,
        vectors_config=VectorParams(
            size=config.vector_size,
            distance=config.distance,
        ),
    )
    return True


def reset_collection(
    client: QdrantClient,
    config: QdrantCollectionConfig,
) -> None:
    if collection_exists(client, config.collection_name):
        client.delete_collection(collection_name=config.collection_name)

    client.create_collection(
        collection_name=config.collection_name,
        vectors_config=VectorParams(
            size=config.vector_size,
            distance=config.distance,
        ),
    )


def to_qdrant_point(
    embedded_chunk: EmbeddedChunk,
    *,
    vector_size: int | None = None,
) -> PointStruct:
    if vector_size is not None and len(embedded_chunk.vector) != vector_size:
        raise ValueError(
            f"vector size mismatch for {embedded_chunk.point_id}: "
            f"expected {vector_size}, got {len(embedded_chunk.vector)}"
        )

    return PointStruct(
        id=qdrant_point_id(embedded_chunk.point_id),
        vector=embedded_chunk.vector,
        payload=embedded_chunk.payload,
    )


def to_qdrant_points(
    embedded_chunks: list[EmbeddedChunk],
    *,
    vector_size: int | None = None,
) -> list[PointStruct]:
    return [
        to_qdrant_point(embedded_chunk, vector_size=vector_size)
        for embedded_chunk in embedded_chunks
    ]


def qdrant_point_id(chunk_id: str) -> str:
    if not chunk_id.strip():
        raise ValueError("chunk_id cannot be empty")
    return str(uuid5(NAMESPACE_URL, f"supportlens:{chunk_id}"))
