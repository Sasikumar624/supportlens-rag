import re
from dataclasses import dataclass
from enum import StrEnum

from app.ingestion.models import LoadedDocumentPart


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    PROCEDURE_STEP = "procedure_step"
    WARNING = "warning"
    NOTE = "note"
    TABLE_ROW = "table_row"


@dataclass(frozen=True)
class StructuredBlock:
    block_id: str
    block_type: BlockType
    text: str
    section: str | None
    page: int | None
    document_id: str
    source_url: str


_PROCEDURE_STEP_PATTERN = re.compile(r"^\d+[.)]\s+")
_LIST_ITEM_PATTERN = re.compile(r"^([-*]|\u2022)\s+")
_WARNING_PATTERN = re.compile(r"^(warning|caution|danger|important)\s*[:\-]", re.IGNORECASE)
_NOTE_PATTERN = re.compile(r"^(note|tip)\s*[:\-]", re.IGNORECASE)


def detect_structure(part: LoadedDocumentPart) -> list[StructuredBlock]:
    blocks: list[StructuredBlock] = []
    current_section = part.section

    for index, raw_block in enumerate(_split_blocks(part.text), start=1):
        block_type = classify_block(raw_block)
        if block_type == BlockType.HEADING:
            current_section = raw_block

        blocks.append(
            StructuredBlock(
                block_id=f"{part.document_id}_B{index:04d}",
                block_type=block_type,
                text=raw_block,
                section=current_section,
                page=part.page,
                document_id=part.document_id,
                source_url=part.source_url,
            )
        )

    return blocks


def classify_block(text: str) -> BlockType:
    stripped = text.strip()

    if _WARNING_PATTERN.match(stripped):
        return BlockType.WARNING

    if _NOTE_PATTERN.match(stripped):
        return BlockType.NOTE

    if _PROCEDURE_STEP_PATTERN.match(stripped):
        return BlockType.PROCEDURE_STEP

    if _LIST_ITEM_PATTERN.match(stripped):
        return BlockType.LIST_ITEM

    if _looks_like_table_row(stripped):
        return BlockType.TABLE_ROW

    if _looks_like_heading(stripped):
        return BlockType.HEADING

    return BlockType.PARAGRAPH


def _split_blocks(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    blocks: list[str] = []
    paragraph_lines: list[str] = []

    for line in lines:
        if not line:
            _flush_paragraph(paragraph_lines, blocks)
            continue

        if _line_should_stand_alone(line):
            _flush_paragraph(paragraph_lines, blocks)
            blocks.append(line)
            continue

        paragraph_lines.append(line)

    _flush_paragraph(paragraph_lines, blocks)
    return blocks


def _flush_paragraph(paragraph_lines: list[str], blocks: list[str]) -> None:
    if paragraph_lines:
        blocks.append(" ".join(paragraph_lines))
        paragraph_lines.clear()


def _line_should_stand_alone(line: str) -> bool:
    return classify_block(line) != BlockType.PARAGRAPH


def _looks_like_heading(text: str) -> bool:
    if len(text) > 90:
        return False
    if text.endswith((".", ",", ";", ":")):
        return False
    words = text.split()
    if not words or len(words) > 10:
        return False
    if text.isupper() and len(words) <= 8:
        return True
    title_words = sum(1 for word in words if word[:1].isupper() or word.isupper())
    return title_words >= max(1, len(words) - 1)


def _looks_like_table_row(text: str) -> bool:
    if "|" in text and text.count("|") >= 2:
        return True
    if "\t" in text:
        return True
    columns = re.split(r"\s{2,}", text)
    return len([column for column in columns if column.strip()]) >= 3
