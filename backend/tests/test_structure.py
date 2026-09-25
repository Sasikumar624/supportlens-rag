from app.ingestion.models import LoadedDocumentPart
from app.ingestion.structure import BlockType, classify_block, detect_structure


def make_part(text: str, section: str | None = None) -> LoadedDocumentPart:
    return LoadedDocumentPart(
        document_id="DOC_TEST",
        title="Router Guide",
        filename="router.html",
        page=None,
        section=section,
        category="troubleshooting",
        product="Router X",
        version="v1",
        language="English",
        source_url="https://example.com/router",
        source_type="html",
        text=text,
    )


def test_classify_block_detects_support_document_shapes() -> None:
    assert classify_block("Factory Reset") == BlockType.HEADING
    assert classify_block("1. Open the admin page.") == BlockType.PROCEDURE_STEP
    assert classify_block("- Check the WAN cable.") == BlockType.LIST_ITEM
    assert classify_block("Warning: Do not power off the router.") == BlockType.WARNING
    assert classify_block("Note: Settings may be erased.") == BlockType.NOTE
    assert classify_block("LED  State  Meaning") == BlockType.TABLE_ROW
    assert classify_block("The router restarts after the update.") == BlockType.PARAGRAPH


def test_detect_structure_tracks_current_section() -> None:
    part = make_part(
        """
        Factory Reset
        1. Hold the reset button for ten seconds.
        2. Wait for the status LED to blink.

        Warning: This erases local settings.

        Recovery Mode
        Use recovery mode if the router does not boot.
        """
    )

    blocks = detect_structure(part)

    assert [block.block_type for block in blocks] == [
        BlockType.HEADING,
        BlockType.PROCEDURE_STEP,
        BlockType.PROCEDURE_STEP,
        BlockType.WARNING,
        BlockType.HEADING,
        BlockType.PARAGRAPH,
    ]
    assert blocks[1].section == "Factory Reset"
    assert blocks[3].section == "Factory Reset"
    assert blocks[5].section == "Recovery Mode"


def test_detect_structure_preserves_source_metadata() -> None:
    part = make_part("Wi-Fi Setup\nSet the country code before enabling Wi-Fi.", section="Initial Setup")

    blocks = detect_structure(part)

    assert blocks[0].document_id == "DOC_TEST"
    assert blocks[0].source_url == "https://example.com/router"
    assert blocks[0].page is None
    assert blocks[0].block_id == "DOC_TEST_B0001"


def test_detect_structure_uses_existing_section_until_heading_changes() -> None:
    part = make_part("Check cable connection.\n- Restart modem.", section="Connectivity")

    blocks = detect_structure(part)

    assert blocks[0].section == "Connectivity"
    assert blocks[1].section == "Connectivity"
