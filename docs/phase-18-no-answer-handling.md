# SupportLens Phase 18 No-Answer Handling

Status: Initial no-answer gate implemented.
Date: 2026-09-28

## Objective

SupportLens must not answer every question. Phase 18 adds deterministic refusal handling before LLM generation so unsupported, irrelevant, or out-of-domain questions do not get turned into hallucinated support answers.

## Completed

- Added `NoAnswerConfig` in `backend/app/rag/generator.py`.
- Added a default refusal response:

```text
I could not find information relevant to that question in the available technical-support documentation.
```

- Added pre-generation refusal checks for:
  - no retrieved context
  - too little usable context text
  - retrieval scores below the configured relevance threshold
- Added `refused` and `no_answer_reason` fields to `GeneratedAnswer`.
- Ensured the LLM client is not called when the no-answer gate refuses a question.
- Added environment settings:
  - `NO_ANSWER_MIN_SCORE`
  - `NO_ANSWER_MIN_CONTEXT_CHARS`
- Expanded `evaluation/dataset.json` with 15 additional unsupported or out-of-domain questions.
- Added unit tests for no-context refusal, low-relevance refusal, disabled-gate experiments, and config validation.

## Current Strategy

The answer flow is now:

```text
question -> retriever -> top context chunks -> no-answer gate
                                      |-> refuse with reason
                                      |-> grounded prompt -> LLM -> answer
```

The first implementation uses conservative heuristics:

- `no_context`: retrieval returned no chunks.
- `insufficient_context`: retrieved chunks do not contain enough text to ground an answer.
- `low_relevance`: the best retrieved score is lower than `NO_ANSWER_MIN_SCORE`.

These checks are deliberately outside the prompt so they work even when a local model ignores instructions.

## Role Responsibilities

The retriever role finds candidate support chunks and provides scores, metadata, and text. It should be tuned to return relevant candidates, but it is not solely responsible for deciding whether the assistant should answer.

The no-answer gate role protects the generation step. It decides whether the retrieved evidence is strong enough to send to the LLM. When evidence is missing or weak, it returns the standard refusal response and a machine-readable reason.

The LLM role writes the final support answer only after the no-answer gate approves the context. It must still follow the grounded prompt rules and avoid unsupported facts.

The evaluator role measures both sides of the behavior:

- supported questions should still receive grounded answers
- unsupported questions should be refused
- irrelevant retrieval should not cause hallucinated answers

The product/API role can use `GeneratedAnswer.refused` and `GeneratedAnswer.no_answer_reason` to display a clear no-answer state in the frontend, log refusal quality, and track whether threshold changes improve or hurt behavior.

## Evaluation Notes

The dataset now includes more unsupported questions across:

- current events
- sports
- financial advice
- user-specific secrets
- device-specific live state
- private account or email data
- unrelated general knowledge tasks

Measure no-answer behavior with at least:

- refusal precision: refused answers that were truly unsupported
- refusal recall: unsupported questions that were correctly refused
- supported-answer retention: answerable questions that were not incorrectly refused
- hallucination rate: unsupported questions that still produced factual-looking answers

## Current Limits

The score threshold is a starting point, not a final value. Different embedding models, Qdrant distance metrics, and chunking strategies can shift score distributions.

Before treating the defaults as production-ready, calibrate `NO_ANSWER_MIN_SCORE` against the evaluation dataset and inspect false positives where answerable questions are refused.
