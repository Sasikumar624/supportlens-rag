# SupportLens Phase 5 Structure Detection

Status: Initial structure detector implemented.
Date: 2026-09-25

## Objective

Phase 5 identifies basic document structure in loaded and cleaned text. The purpose is to improve later chunking and citation quality without overclaiming perfect document understanding.

## Completed

- Added `backend/app/ingestion/structure.py`.
- Added block types for:
  - headings
  - paragraphs
  - list items
  - numbered procedure steps
  - warnings
  - notes
  - table-like rows
- Added `detect_structure()` for converting a loaded document part into structured blocks.
- Added section tracking so blocks inherit the most recent heading or existing loaded section.
- Added stable block IDs such as `DOC001_B0001`.
- Added tests for classification, section tracking, metadata preservation, and existing-section handling.

## Why This Matters

Chunking should not blindly split text by character count. Support documents often contain procedures, warnings, and troubleshooting sections. Detecting these structures early helps later phases avoid chunks that mix unrelated topics or split important steps.

## Current Limits

This is heuristic detection. It does not yet perform advanced layout analysis, table reconstruction, nested list parsing, or semantic heading classification.

Those improvements can come later if measured retrieval quality shows they are needed.

