# SupportLens Phase 3 Document Loading

Status: Initial PDF and HTML loaders implemented.
Date: 2026-09-25

## Objective

Phase 3 adds the first document-loading layer. The loader output must preserve source metadata instead of collapsing documents into one anonymous string.

## Completed

- Added ingestion data models for source records and loaded document parts.
- Added `load_sources_csv()` for reading `data/sources.csv`.
- Added a PDF loader using PyMuPDF.
- Added an HTML loader using BeautifulSoup.
- Added `load_document()` dispatch based on `source_type`.
- Added tests for source CSV loading, HTML extraction, metadata preservation, PDF page loading, and loader dispatch.
- Added `beautifulsoup4` as an explicit backend dependency.

## Loader Output

Each loaded part preserves:

- `document_id`
- `title`
- `filename`
- `page`
- `section`
- `category`
- `product`
- `version`
- `language`
- `source_url`
- `source_type`
- `text`

## Current Scope

The loaders do minimal extraction only. They do not perform full cleaning, section detection, chunking, embedding, or indexing yet.

Those belong to later phases:

- Phase 4: text cleaning
- Phase 5: section and structure detection
- Phase 6: chunking
- Phase 10: indexing pipeline

## Notes

The Phase 2 Stage A source registry uses HTML OpenWrt documentation pages. Supporting HTML in Phase 3 lets the project proceed with those official sources while still satisfying the plan's requirement to support PDF loading early.
