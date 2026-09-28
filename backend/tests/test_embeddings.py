from app.ingestion.chunker import ChunkingConfig, chunk_blocks
from app.ingestion.structure import BlockType, StructuredBlock
from app.rag.embeddings import (
    EmbeddingConfig,
    EmbeddingModel,
    cosine_similarity,
    normalize_vector,
)


class FakeEncoder:
    def __init__(self) -> None:
        self.seen_sentences: list[list[str]] = []

    def encode(
        self,
        sentences,
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ):
        self.seen_sentences.append(list(sentences))
        return [[float(len(sentence)), float(sentence.count("router"))] for sentence in sentences]

    def get_sentence_embedding_dimension(self) -> int:
        return 2


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


def test_embed_texts_batches_and_normalizes_vectors() -> None:
    encoder = FakeEncoder()
    model = EmbeddingModel(
        EmbeddingConfig(model_name="fake-model", batch_size=2),
        encoder=encoder,
    )

    vectors = model.embed_texts(["router setup", "reset router"])

    assert encoder.seen_sentences == [["router setup", "reset router"]]
    assert len(vectors) == 2
    assert round(sum(value * value for value in vectors[0]), 6) == 1.0
    assert model.dimension == 2


def test_embed_query_adds_bge_query_instruction() -> None:
    encoder = FakeEncoder()
    model = EmbeddingModel(EmbeddingConfig(model_name="fake-model"), encoder=encoder)

    model.embed_query("How do I reset the router?")

    assert encoder.seen_sentences[0][0].startswith(
        "Represent this sentence for searching relevant passages: "
    )
    assert encoder.seen_sentences[0][0].endswith("How do I reset the router?")


def test_embed_chunks_returns_vectors_with_qdrant_ready_payloads() -> None:
    chunks = chunk_blocks(
        [
            block(1, "Factory Reset"),
            block(2, "Hold the router reset button for ten seconds."),
        ],
        ChunkingConfig(target_tokens=50, overlap_blocks=0),
    )
    model = EmbeddingModel(EmbeddingConfig(model_name="fake-model"), encoder=FakeEncoder())

    embedded = model.embed_chunks(chunks)

    assert len(embedded) == 1
    assert embedded[0].point_id == "DOC_TEST_C0001"
    assert embedded[0].payload["chunk_id"] == "DOC_TEST_C0001"
    assert embedded[0].payload["text"] == chunks[0].text
    assert len(embedded[0].vector) == 2


def test_vector_helpers_validate_dimensions_and_zero_vectors() -> None:
    assert normalize_vector([3.0, 4.0]) == [0.6, 0.8]
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0

    try:
        normalize_vector([0.0, 0.0])
    except ValueError as error:
        assert "zero vector" in str(error)
    else:
        raise AssertionError("Expected zero vector validation error")

    try:
        cosine_similarity([1.0], [1.0, 2.0])
    except ValueError as error:
        assert "same dimension" in str(error)
    else:
        raise AssertionError("Expected dimension validation error")
