import re
from dataclasses import dataclass

from app.ingestion.structure import BlockType, StructuredBlock


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    source_url: str
    page: int | None
    section: str | None
    text: str
    token_count: int
    block_ids: list[str]
    block_types: list[str]

    @property
    def metadata(self) -> dict[str, str | int | list[str] | None]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source_url": self.source_url,
            "page": self.page,
            "section": self.section,
            "token_count": self.token_count,
            "block_ids": self.block_ids,
            "block_types": self.block_types,
        }


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 500
    overlap_blocks: int = 1

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be positive")
        if self.overlap_blocks < 0:
            raise ValueError("overlap_blocks cannot be negative")


def chunk_blocks(
    blocks: list[StructuredBlock],
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    if not blocks:
        return []

    config = config or ChunkingConfig()
    chunks: list[Chunk] = []
    current: list[StructuredBlock] = []

    for block in blocks:
        if _starts_new_chunk(block, current):
            _append_chunk(chunks, current)
            current = _overlap_tail(current, config.overlap_blocks)

        projected = current + [block]
        if current and _count_tokens(_join_blocks(projected)) > config.target_tokens:
            _append_chunk(chunks, current)
            current = _overlap_tail(current, config.overlap_blocks)

        current.append(block)

    _append_chunk(chunks, current)
    return chunks


def _starts_new_chunk(block: StructuredBlock, current: list[StructuredBlock]) -> bool:
    if not current:
        return False
    if block.block_type != BlockType.HEADING:
        return False
    return block.section != current[-1].section


def _append_chunk(chunks: list[Chunk], blocks: list[StructuredBlock]) -> None:
    if not blocks:
        return

    first = blocks[0]
    chunk_index = len(chunks) + 1
    text = _join_blocks(blocks)
    block_types = [block.block_type.value for block in blocks]

    chunks.append(
        Chunk(
            chunk_id=f"{first.document_id}_C{chunk_index:04d}",
            document_id=first.document_id,
            source_url=first.source_url,
            page=_first_non_none_page(blocks),
            section=_dominant_section(blocks),
            text=text,
            token_count=_count_tokens(text),
            block_ids=[block.block_id for block in blocks],
            block_types=block_types,
        )
    )


def _overlap_tail(blocks: list[StructuredBlock], overlap_blocks: int) -> list[StructuredBlock]:
    if overlap_blocks == 0:
        return []

    tail: list[StructuredBlock] = []
    for block in reversed(blocks):
        if block.block_type == BlockType.HEADING and tail:
            break
        tail.insert(0, block)
        if len(tail) >= overlap_blocks:
            break
    return tail


def _join_blocks(blocks: list[StructuredBlock]) -> str:
    return "\n\n".join(block.text for block in blocks if block.text.strip())


def _count_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _first_non_none_page(blocks: list[StructuredBlock]) -> int | None:
    for block in blocks:
        if block.page is not None:
            return block.page
    return None


def _dominant_section(blocks: list[StructuredBlock]) -> str | None:
    for block in reversed(blocks):
        if block.section:
            return block.section
    return None
