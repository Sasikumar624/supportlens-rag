# SupportLens Phase 19 Citations

Status: Initial citation layer implemented.
Date: 2026-09-28

## Objective

Every supported answer should carry source information that a user or frontend can inspect. Citations must connect the generated answer back to the retrieved chunks used as evidence.

## Completed

- Expanded retrieval results with citation metadata accessors for:
  - document title
  - page
  - section
  - source URL
  - product
  - version
  - category
- Expanded `SourceCitation` in `backend/app/rag/generator.py` so generated answers return structured citation records.
- Added `GeneratedAnswer.answer_with_citations` for plain-text output that appends a `Sources:` block after supported answers.
- Kept refused no-answer responses citation-free, because unsupported answers should not imply evidence exists.
- Added source URL, product, version, and category to the grounded prompt context header so bracketed source numbers map to richer evidence.
- Added tests for citation labels, clickable Markdown citations, source metadata, and refused-answer behavior.

## Current Strategy

The answer flow is now:

```text
question -> retriever -> context chunks -> no-answer gate
                                      |-> refuse without sources
                                      |-> grounded prompt with Source [n] metadata
                                      |-> LLM answer with [n]
                                      |-> structured SourceCitation records
```

The LLM is asked to cite using bracketed source numbers such as `[1]`. The application also returns a structured `sources` list with the same numbering. This keeps display concerns out of the model and gives the future frontend stable fields for clickable citations.

## Role Responsibilities

The ingestion role preserves citation metadata when documents are loaded and chunked. It is responsible for carrying title, page, section, source URL, product, version, category, and document identifiers into chunk metadata.

The indexing role stores those metadata fields in Qdrant payloads with each vector. If a field is missing at indexing time, later retrieval and citation rendering cannot recover it reliably.

The retriever role returns the evidence chunks and exposes citation fields from Qdrant payloads through `RetrievalResult`. It owns ranking and source numbering order indirectly because the generated citations follow the retrieved chunk order.

The no-answer gate role decides whether evidence is strong enough to cite. If it refuses a question, it returns no citations so the product does not display irrelevant sources as support.

The LLM role writes the answer and uses bracketed source numbers. It should not invent document names, pages, URLs, or product versions because those are supplied separately as structured metadata.

The product/API role should display `GeneratedAnswer.sources` next to the answer. When `source_url` exists, the frontend can render the citation as a clickable link. When page, section, product, or version exists, it should show those details to help users verify the answer.

The evaluator role checks citation correctness, not only answer quality. A supported answer should cite relevant retrieved chunks, and unsupported answers should be refused without citations.

## Current Limits

Citation correctness still depends on retrieval quality and the metadata produced by ingestion. Phase 19 does not yet verify that every bracketed citation in the model text exactly matches the best evidence span.

Future evaluation should measure:

- answers with at least one citation
- citation relevance to the answer
- missing source metadata rates
- hallucinated citation markers not present in `sources`
- user-facing citation clickability in the frontend
