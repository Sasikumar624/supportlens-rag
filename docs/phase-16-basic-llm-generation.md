# SupportLens Phase 16 Basic LLM Generation

Status: Initial grounded generation interface implemented.
Date: 2026-09-28

## Objective

Phase 16 connects retrieval results to a grounded prompt and an LLM client interface.

This phase defines how SupportLens should ask an LLM to answer from retrieved evidence. It does not select the final local model yet.

## Completed

- Added `backend/app/rag/generator.py`.
- Added grounded prompt construction with rules to:
  - use only supplied context
  - avoid unsupported facts
  - state when context is insufficient
  - prefer concise support steps
  - preserve warnings and cautions
  - cite sources with bracketed source numbers
- Added `RAGPipeline` for:
  - accepting a user question
  - retrieving context chunks
  - building a grounded prompt
  - calling an LLM client
  - returning an answer with source citations
- Added `SourceCitation` and `GeneratedAnswer` result records.
- Added `PromptConfig` for limiting context chunks sent to the prompt.
- Added an `UnsupportedLLMClient` that raises a clear error until Phase 17 wires a local model.
- Added tests with fake retrievers and fake LLM clients.

## Current Strategy

The generation flow is:

```text
question -> retriever -> context chunks -> grounded prompt -> LLM client -> answer + sources
```

The LLM is deliberately injected behind a small interface so the project can evaluate the local model choice in Phase 17 instead of hard-coding it too early.

## Current Limits

This phase does not yet run a real local Hugging Face generation model.

It also does not fully evaluate answer faithfulness, no-answer behavior, or citation correctness. Those belong to later phases.
