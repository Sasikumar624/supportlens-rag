import csv
import re
from pathlib import Path
from urllib.request import Request, urlopen

import fitz
from bs4 import BeautifulSoup

from app.ingestion.models import LoadedDocumentPart, SourceRecord, filename_or_none


def load_sources_csv(path: Path) -> list[SourceRecord]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [SourceRecord.from_csv_row(row) for row in csv.DictReader(csv_file)]


def load_document(
    source: SourceRecord,
    *,
    local_path: Path | None = None,
) -> list[LoadedDocumentPart]:
    source_type = source.source_type.strip().lower()

    if source_type == "pdf":
        if local_path is None:
            raise ValueError("PDF sources require a local_path")
        return PdfLoader().load(source, local_path)

    if source_type == "html":
        return HtmlLoader().load(source, local_path=local_path)

    raise ValueError(f"Unsupported source_type: {source.source_type}")


class PdfLoader:
    def load(self, source: SourceRecord, path: Path) -> list[LoadedDocumentPart]:
        if not path.exists():
            raise FileNotFoundError(path)

        parts: list[LoadedDocumentPart] = []

        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                text = _normalize_text(page.get_text("text"))
                if not text:
                    continue

                parts.append(
                    LoadedDocumentPart(
                        document_id=source.document_id,
                        title=source.title,
                        filename=filename_or_none(path),
                        page=page_index,
                        section=None,
                        category=source.category,
                        product=source.product,
                        version=source.version,
                        language=source.language,
                        source_url=source.source_url,
                        source_type=source.source_type,
                        text=text,
                    )
                )

        return parts


class HtmlLoader:
    def load(
        self,
        source: SourceRecord,
        *,
        local_path: Path | None = None,
        html: str | None = None,
    ) -> list[LoadedDocumentPart]:
        if html is None:
            html = self._read_html(source, local_path)

        soup = BeautifulSoup(html, "html.parser")

        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        content = _select_main_content(soup)
        section = _first_heading(content)
        text = _normalize_text(content.get_text(separator="\n"))

        if not text:
            return []

        return [
            LoadedDocumentPart(
                document_id=source.document_id,
                title=source.title,
                filename=filename_or_none(local_path),
                page=None,
                section=section,
                category=source.category,
                product=source.product,
                version=source.version,
                language=source.language,
                source_url=source.source_url,
                source_type=source.source_type,
                text=text,
            )
        ]

    def _read_html(self, source: SourceRecord, local_path: Path | None) -> str:
        if local_path is not None:
            return local_path.read_text(encoding="utf-8")

        request = Request(
            source.source_url,
            headers={"User-Agent": "SupportLens-RAG/0.1 document loader"},
        )
        with urlopen(request, timeout=20) as response:
            encoding = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(encoding, errors="replace")


def _select_main_content(soup: BeautifulSoup):
    selectors = [
        "main",
        "article",
        "#dokuwiki__content",
        ".page",
        "#content",
        "body",
    ]
    for selector in selectors:
        content = soup.select_one(selector)
        if content is not None:
            return content
    return soup


def _first_heading(content) -> str | None:
    heading = content.find(["h1", "h2", "h3"])
    if heading is None:
        return None
    text = _normalize_text(heading.get_text(" "))
    return text or None


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
