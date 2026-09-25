from app.ingestion.chunker import ChunkingConfig, chunk_blocks
from app.ingestion.structure import BlockType, StructuredBlock


def block(
    index: int,
    text: str,
    block_type: BlockType = BlockType.PARAGRAPH,
    section: str | None = "Setup",
) -> StructuredBlock:
    return StructuredBlock(
        block_id=f"DOC_TEST_B{index:04d}",
        block_type=block_type,
        text=text,
        section=section,
        page=1,
        document_id="DOC_TEST",
        source_url="https://example.com/router",
    )


def test_chunk_blocks_preserves_metadata_and_stable_ids() -> None:
    chunks = chunk_blocks(
        [
            block(1, "Setup", BlockType.HEADING, "Setup"),
            block(2, "Connect the WAN cable."),
        ],
        ChunkingConfig(target_tokens=50, overlap_blocks=0),
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "DOC_TEST_C0001"
    assert chunks[0].document_id == "DOC_TEST"
    assert chunks[0].source_url == "https://example.com/router"
    assert chunks[0].page == 1
    assert chunks[0].section == "Setup"
    assert chunks[0].block_ids == ["DOC_TEST_B0001", "DOC_TEST_B0002"]
    assert chunks[0].metadata["chunk_id"] == "DOC_TEST_C0001"


def test_chunk_blocks_splits_when_target_size_is_exceeded() -> None:
    chunks = chunk_blocks(
        [
            block(1, "Setup", BlockType.HEADING),
            block(2, "one two three four five six"),
            block(3, "seven eight nine ten eleven twelve"),
        ],
        ChunkingConfig(target_tokens=8, overlap_blocks=0),
    )

    assert len(chunks) == 2
    assert "one two three" in chunks[0].text
    assert "seven eight nine" in chunks[1].text


def test_chunk_blocks_starts_new_chunk_on_new_heading() -> None:
    chunks = chunk_blocks(
        [
            block(1, "Factory Reset", BlockType.HEADING, "Factory Reset"),
            block(2, "Hold the reset button.", BlockType.PROCEDURE_STEP, "Factory Reset"),
            block(3, "Firmware Upgrade", BlockType.HEADING, "Firmware Upgrade"),
            block(4, "Upload the sysupgrade image.", BlockType.PROCEDURE_STEP, "Firmware Upgrade"),
        ],
        ChunkingConfig(target_tokens=50, overlap_blocks=0),
    )

    assert len(chunks) == 2
    assert chunks[0].section == "Factory Reset"
    assert chunks[1].section == "Firmware Upgrade"
    assert "Firmware Upgrade" in chunks[1].text


def test_chunk_blocks_can_overlap_previous_context() -> None:
    chunks = chunk_blocks(
        [
            block(1, "Setup", BlockType.HEADING),
            block(2, "alpha beta gamma delta epsilon"),
            block(3, "zeta eta theta iota kappa"),
        ],
        ChunkingConfig(target_tokens=6, overlap_blocks=1),
    )

    assert len(chunks) == 2
    assert chunks[1].block_ids[0] == "DOC_TEST_B0002"


def test_chunking_config_rejects_invalid_values() -> None:
    try:
        ChunkingConfig(target_tokens=0)
    except ValueError as error:
        assert "target_tokens" in str(error)
    else:
        raise AssertionError("Expected target_tokens validation error")

    try:
        ChunkingConfig(overlap_blocks=-1)
    except ValueError as error:
        assert "overlap_blocks" in str(error)
    else:
        raise AssertionError("Expected overlap_blocks validation error")
