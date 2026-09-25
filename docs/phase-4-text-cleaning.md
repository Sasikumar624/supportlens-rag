# SupportLens Phase 4 Text Cleaning

Status: Initial text cleaner implemented and wired into document loaders.
Date: 2026-09-25

## Objective

Phase 4 adds conservative text cleaning for extracted support documentation.

The cleaner should improve retrieval quality without damaging technical content. It must preserve exact identifiers, error codes, numbered procedures, warnings, and source metadata.

## Completed

- Added `backend/app/ingestion/cleaner.py`.
- Moved generic text normalization out of the loaders.
- Wired PDF and HTML loaders to use `clean_text()`.
- Added tests for:
  - broken error-code repair
  - exact identifier preservation
  - numbered procedure preservation
  - hyphenated line-break repair
  - control-character removal
  - repeated blank-line collapse

## Cleaning Rules

The current cleaner performs:

- CRLF/CR line-ending normalization
- control-character removal
- hyphenated line-break repair
- broken technical identifier repair, such as `ERROR\n105` to `ERROR 105`
- soft line-break repair for paragraph text
- repeated horizontal whitespace normalization
- excessive blank-line collapse

## Non-Goals

The cleaner does not yet remove repeated headers/footers, detect full document structure, preserve complex tables, or infer sections. Those belong to later phases.

## Principle

Do not over-clean.

Technical information must remain intact, especially:

- error codes
- firmware versions
- model numbers
- IP addresses
- numbered procedures
- warnings and notes
