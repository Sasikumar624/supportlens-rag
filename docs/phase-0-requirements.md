# SupportLens Phase 0 Requirements

Status: Locked for initial implementation
Date: 2026-09-25

## Project Identity

Project name: SupportLens

Project type: Production-style technical-support Retrieval-Augmented Generation application.

Project statement:

SupportLens is a technical-support RAG assistant that retrieves evidence from a multi-document support knowledge base and generates grounded, source-cited answers. It must refuse to answer when the indexed documents do not provide sufficient evidence.

SupportLens is not a general chatbot. It is a support assistant for trusted product-support documentation.

## Locked Domain

Initial domain: Networking, router, and connectivity support.

The detailed domain contract is maintained in [SupportLens Domain Specification](domain-specification.md). Phase 0 locks the product boundary; the domain specification expands that boundary into users, source requirements, metadata expectations, evaluation coverage, and UI implications.

Production framing:

SupportLens should behave like a support knowledge-base assistant for customer networking equipment and connectivity workflows. It should help users and support agents answer documented questions about router setup, firmware maintenance, local network configuration, Wi-Fi configuration, connectivity troubleshooting, recovery procedures, and related product-support policies.

Primary users:

- Home or small-office router users who need clear setup and troubleshooting guidance
- Tier-1 support agents who need fast cited answers while helping customers
- Network administrators who need quick references for firmware, Wi-Fi, LAN/WAN, and recovery tasks
- Documentation or QA reviewers who need to evaluate support coverage

In-scope support areas:

- Product manuals and user guides
- Setup and installation guides
- Wi-Fi, LAN, WAN, DHCP, DNS, firewall, and routing configuration documents
- Firmware update, sysupgrade, release, and migration guidance
- Troubleshooting procedures for connectivity, access loss, upgrade failures, and reset/recovery workflows
- Error codes, model numbers, hardware revisions, firmware versions, and IP-address-related support references
- FAQ/help articles
- Warranty, support, maintenance, and service-policy documents

Out-of-scope areas:

- Medical, legal, financial, vehicle, or unrelated consumer-electronics advice
- Generic programming documentation unrelated to indexed networking support documents
- Live device telemetry or network diagnosis that the system cannot observe
- Security exploitation, credential bypass, or unsafe device access guidance
- Product claims or recommendations not supported by indexed evidence

The first implementation should not mix unrelated domains such as healthcare, vehicle manuals, generic programming docs, or unrelated consumer electronics.

Current seed corpus:

The current Stage A dataset uses official OpenWrt documentation because it is a realistic seed product inside the locked domain. OpenWrt is not the entire domain; it is the first source family used to validate ingestion, cleaning, retrieval, grounded generation, citations, evaluation, and frontend behavior.

## Dataset Scope

Development will grow in three stages.

Stage A: Smoke test

- 3-5 documents
- PDF support first
- Goal: prove loading, cleaning, chunking, embeddings, Qdrant indexing, and dense retrieval

Stage B: Intermediate dataset

- About 20 documents
- Goal: validate metadata, duplicate/similar information, retrieval across multiple products or document types, and the first evaluation questions

Stage C: Final dataset

- 50-100 useful sources
- About 2,000-6,000 indexed chunks
- 100-150 evaluation questions
- Goal: final retrieval experiments, RAG evaluation, public demo, and resume-ready metrics

## Document Categories

Target source categories:

- Product/user manuals
- Installation and setup guides
- Troubleshooting guides
- FAQ and help articles
- Configuration guides
- Warranty and support policies
- Technical/reference documents
- Firmware or release guidance where available

Every document must have provenance metadata before indexing.

Required source metadata:

- `document_id`
- `title`
- `category`
- `source_url`
- `product`
- `version`
- `language`
- `retrieval_date`
- `license`
- `notes`

Copyright rule:

Do not commit third-party PDFs unless redistribution is clearly allowed. When rights are unclear, keep source URLs, metadata, and ingestion instructions instead of storing the raw document in GitHub.

## Core Features

Phase 0 locks the following final feature direction:

- Document ingestion with metadata preservation
- PDF loading first, with HTML/TXT/Markdown/DOCX only when needed
- Text cleaning that preserves technical identifiers, numbered procedures, warnings, and tables where possible
- Chunking experiments using fixed-size and structure-aware strategies
- Hugging Face/Sentence Transformers embeddings
- Qdrant vector storage with metadata payloads
- Dense retrieval as the first retrieval method
- Metadata filtering after baseline dense retrieval works
- Reranking after retrieval quality is measurable
- Keyword/BM25 retrieval for exact identifiers
- Hybrid retrieval with result fusion
- Grounded LLM answer generation
- No-answer behavior for unsupported questions
- Source citations for supported answers
- FastAPI backend
- Minimal Next.js frontend after retrieval and generation are stable
- Feedback capture
- Docker-based local development
- GitHub Actions CI
- Public demo deployment after the system is evaluated

## Initial Architecture

Version 1 must stay simple:

1. User question
2. Query embedding
3. Qdrant dense search
4. Top chunks
5. Grounded prompt
6. LLM answer
7. Citations or no-answer response

Advanced retrieval must be added only after the dense baseline is working and measurable.

## Evaluation Strategy

Evaluation is required, not optional.

Retrieval evaluation:

- Hit Rate
- Recall@1
- Recall@3
- Recall@5
- MRR

Generation evaluation:

- Faithfulness
- Answer relevance
- Context precision
- Context recall
- Citation correctness
- No-answer correctness

Evaluation dataset requirements:

- 100-150 final questions
- Include answerable and unanswerable questions
- Include setup, troubleshooting, configuration, procedure, exact identifier, product/model, multi-chunk, and multi-document questions
- Include about 15-20 unsupported or out-of-domain questions
- Store expected evidence using stable source identifiers, preferably `document_id`, `section`, and eventually expected `chunk_id` values

No resume or README metric may be claimed until it is measured.

## Locked Initial Stack

- Language: Python
- Backend: FastAPI, Pydantic
- PDF parsing: PyMuPDF
- Embeddings: Sentence Transformers
- Initial embedding model: `BAAI/bge-small-en-v1.5`
- Vector database: Qdrant
- Sparse retrieval: BM25 or equivalent
- Reranker: cross-encoder reranker, initial candidate `cross-encoder/ms-marco-MiniLM-L6-v2`
- Evaluation: custom retrieval metrics, RAGAS where useful, manual review
- Testing: Pytest
- Frontend: Next.js / React
- Local services: Docker Compose
- CI/CD: GitHub Actions
- Public frontend target: Vercel
- Public backend target: Render or suitable alternative
- Public vector database target: Qdrant Cloud
- Production LLM: to be selected after quality, latency, RAM, availability, and cost are measured

## API Direction

Minimum backend endpoints:

- `GET /health`
- `POST /api/query`
- `GET /api/documents`
- `POST /api/documents`
- `DELETE /api/documents/{id}`
- `POST /api/feedback`

Useful later endpoints:

- `POST /api/reindex`
- `GET /api/stats`
- `GET /api/retrieval-debug/{request_id}`

Query responses should include a stable `request_id` so feedback and retrieval debugging can be tied to the same interaction.

## Security and Safety Requirements

- Keep secrets in environment variables
- Commit `.env.example`, never `.env`
- Validate file type and size for uploads
- Limit input length
- Restrict CORS before public deployment
- Avoid logging secrets or unnecessary sensitive content
- Treat retrieved document content as data, not instructions
- Use prompts that explicitly isolate retrieved text from system/developer instructions
- Return no-answer responses when evidence is insufficient

## Public Demo Expectations

The final public demo should show:

- Knowledge base statistics
- A factual support question
- A troubleshooting question
- An exact identifier or error-code question
- Source citations
- Retrieval details for demonstration/debugging
- A correctly refused unsupported question
- Feedback capture

The frontend should be clean and usable, but the main project value is measured RAG quality, not a heavy UI.

## Phase 0 Exit Criteria

Phase 0 is complete when:

- Project name is locked
- Domain is locked
- Dataset stages are defined
- Document categories are defined
- Core features are defined
- Initial architecture is defined
- Evaluation strategy is defined
- Initial technology stack is defined
- Public-demo expectations are defined
- The next implementation phase can begin without ambiguity
