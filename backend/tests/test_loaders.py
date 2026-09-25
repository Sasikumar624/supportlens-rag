from pathlib import Path

import fitz

from app.ingestion.loaders import HtmlLoader, PdfLoader, load_document, load_sources_csv
from app.ingestion.models import SourceRecord


def make_source(source_type: str = "html") -> SourceRecord:
    return SourceRecord(
        document_id="DOC_TEST",
        title="Test Router Guide",
        category="setup",
        source_url="https://example.com/router-guide",
        product="Test Router",
        version="v1",
        language="English",
        retrieval_date="2026-09-25",
        license="Test fixture",
        notes="Fixture source",
        source_type=source_type,
        raw_storage_policy="test_only",
    )


def test_load_sources_csv_reads_phase_2_registry() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sources = load_sources_csv(repo_root / "data" / "sources.csv")

    assert len(sources) == 5
    assert sources[0].document_id == "DOC001"
    assert sources[0].source_type == "html"


def test_html_loader_preserves_metadata_and_extracts_text() -> None:
    html = """
    <html>
      <body>
        <nav>Navigation noise</nav>
        <main>
          <h1>Factory Reset</h1>
          <p>Press and hold the reset button for ten seconds.</p>
          <script>ignoreMe()</script>
        </main>
      </body>
    </html>
    """

    parts = HtmlLoader().load(make_source(), html=html)

    assert len(parts) == 1
    assert parts[0].document_id == "DOC_TEST"
    assert parts[0].section == "Factory Reset"
    assert parts[0].page is None
    assert "Press and hold" in parts[0].text
    assert "ignoreMe" not in parts[0].text
    assert parts[0].metadata["source_url"] == "https://example.com/router-guide"


def test_pdf_loader_returns_one_part_per_text_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "router.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Router setup page")
    document.save(pdf_path)
    document.close()

    parts = PdfLoader().load(make_source("pdf"), pdf_path)

    assert len(parts) == 1
    assert parts[0].filename == "router.pdf"
    assert parts[0].page == 1
    assert parts[0].section is None
    assert "Router setup page" in parts[0].text


def test_load_document_dispatches_by_source_type(tmp_path: Path) -> None:
    html_path = tmp_path / "guide.html"
    html_path.write_text("<main><h1>Wi-Fi Setup</h1><p>Set country code.</p></main>", encoding="utf-8")

    parts = load_document(make_source("html"), local_path=html_path)

    assert len(parts) == 1
    assert parts[0].filename == "guide.html"
    assert parts[0].section == "Wi-Fi Setup"
