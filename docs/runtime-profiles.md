# Runtime Profiles

Status: Recommended local setup
Date: 2026-10-01

SupportLens has two separate quality problems to balance:

- Retrieval accuracy: finding the right source chunks.
- Answer latency: returning a response before the UI feels stuck.

The current recommended local profile is `high-accuracy retrieval with guarded generation`.

## High-Accuracy Retrieval With Guarded Generation

This is the current project default:

```env
DENSE_RETRIEVAL_ENABLED=true
KEYWORD_RETRIEVAL_TOP_K=10
RERANKING_ENABLED=true
LLM_GENERATION_ENABLED=true
LLM_GENERATION_TIMEOUT_SECONDS=8
```

This profile uses dense retrieval, BM25 keyword search, and cross-encoder reranking. It then attempts local LLM generation with a timeout. If the generation model is missing, slow, or returns an invalid answer, the API falls back to fast cited extractive answers.

Use this profile when:

- the embedding and reranker models are already cached locally
- Qdrant is already indexed
- you want better retrieval quality than keyword-only mode
- you still need the UI to return even when local text generation fails

Tradeoff:

- Startup and query latency are higher than keyword-only mode.
- The first generated answer may fall back to extractive mode if the generation model is not cached.
- True generated prose requires the configured generation model to be available locally.

## Stable Local Fallback Profile

Use this if local model loading fails or the UI becomes slow:

```env
DENSE_RETRIEVAL_ENABLED=false
KEYWORD_RETRIEVAL_TOP_K=10
RERANKING_ENABLED=false
LLM_GENERATION_ENABLED=false
```

This profile avoids loading Hugging Face models during API startup or query handling. It returns fast cited extractive answers from Qdrant payloads and BM25 keyword search.

Use this profile when:

- the UI must return answers quickly
- local model loading is slow or unreliable
- Qdrant is already indexed
- you want grounded citations more than polished prose

Tradeoff:

- Lower semantic recall for vague questions.
- Less polished natural-language synthesis.
- More dependence on exact product/support terms.

## Balanced Accuracy Profile

Try this only after the embedding model loads quickly from local cache:

```env
DENSE_RETRIEVAL_ENABLED=true
KEYWORD_RETRIEVAL_TOP_K=10
RERANKING_ENABLED=false
LLM_GENERATION_ENABLED=false
```

This improves semantic retrieval while still avoiding slow generation. It is usually the next best step after stable-local mode.

## Full ML Retrieval Profile

Use this only on a machine where model startup and query latency have been measured:

```env
DENSE_RETRIEVAL_ENABLED=true
KEYWORD_RETRIEVAL_TOP_K=10
RERANKING_ENABLED=true
LLM_GENERATION_ENABLED=false
```

This is now the default high-accuracy retrieval profile. If it is too slow on a local machine, fall back to stable-local.

## Generation Profile

Generation is enabled by default with timeout/fallback:

```env
LLM_GENERATION_ENABLED=true
LLM_GENERATION_TIMEOUT_SECONDS=8
```

If generation causes latency or memory issues on a specific machine, disable only `LLM_GENERATION_ENABLED`; keep dense retrieval and reranking enabled for better retrieval accuracy.

## Current Recommendation

Use high-accuracy retrieval with guarded generation now. Reranking and dense retrieval can be disabled temporarily if model startup or response time becomes unacceptable on a specific machine.
