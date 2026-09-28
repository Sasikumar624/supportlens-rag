# SupportLens Phase 17 Local Hugging Face LLM

Status: Initial local Hugging Face generation client implemented.
Date: 2026-09-28

## Objective

Phase 17 adds a small local Hugging Face LLM client behind the Phase 16 generation interface.

The goal is to learn and evaluate local model loading, tokenizer use, prompt inference, latency, and answer quality before choosing any final production LLM.

## Completed

- Added `backend/app/rag/local_llm.py`.
- Added `LocalLLMConfig` for:
  - model name
  - max new tokens
  - temperature
  - sampling mode
  - max input tokens
- Added `LocalHuggingFaceLLMClient`.
- Added `.from_settings()` support using environment settings.
- Added explicit `transformers` dependency.
- Updated `.env.example` with local LLM settings.
- Added tests with fake tokenizer and fake model objects so unit tests do not download model weights.

## Current Strategy

The default local model is:

```text
Qwen/Qwen2.5-1.5B-Instruct
```

This is a stronger small instruct model candidate for local development than `google/flan-t5-small`. It should still be evaluated before being treated as the final project model.

The client flow is:

```text
grounded prompt -> tokenizer -> local Hugging Face model.generate() -> decoded answer
```

The client supports:

- causal/chat models through `AutoModelForCausalLM`
- seq2seq models such as FLAN-T5 through `AutoModelForSeq2SeqLM`

Useful local candidates to compare:

- `Qwen/Qwen2.5-1.5B-Instruct` with `LLM_MODEL_TYPE=causal`
- `HuggingFaceTB/SmolLM2-1.7B-Instruct` with `LLM_MODEL_TYPE=causal`
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` with `LLM_MODEL_TYPE=causal`
- `google/flan-t5-base` with `LLM_MODEL_TYPE=seq2seq`

## Current Limits

The model has not been evaluated for final answer quality yet.

Before using it as the final generation model, measure:

- RAM usage
- latency
- answer quality
- faithfulness to retrieved context
- citation behavior
- no-answer behavior
