from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceRecord:
    document_id: str
    title: str
    category: str
    source_url: str
    product: str
    version: str
    language: str
    retrieval_date: str
    license: str
    notes: str
    source_type: str
    raw_storage_policy: str

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "SourceRecord":
        return cls(
            document_id=row["document_id"],
            title=row["title"],
            category=row["category"],
            source_url=row["source_url"],
            product=row["product"],
            version=row["version"],
            language=row["language"],
            retrieval_date=row["retrieval_date"],
            license=row["license"],
            notes=row["notes"],
            source_type=row["source_type"],
            raw_storage_policy=row["raw_storage_policy"],
        )


@dataclass(frozen=True)
class LoadedDocumentPart:
    document_id: str
    title: str
    filename: str | None
    page: int | None
    section: str | None
    category: str
    product: str
    version: str
    language: str
    source_url: str
    source_type: str
    text: str

    @property
    def metadata(self) -> dict[str, str | int | None]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "filename": self.filename,
            "page": self.page,
            "section": self.section,
            "category": self.category,
            "product": self.product,
            "version": self.version,
            "language": self.language,
            "source_url": self.source_url,
            "source_type": self.source_type,
        }


def filename_or_none(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.name
