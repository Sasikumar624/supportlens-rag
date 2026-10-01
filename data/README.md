# SupportLens Data Directory

This directory tracks dataset metadata and reproducible collection structure.

The locked project domain is networking, router, and connectivity support. See `docs/domain-specification.md` for the production domain contract.

The current `sources.csv` entries are a Stage B seed registry with 21 official support sources across OpenWrt, TP-Link, NETGEAR, and ASUS. They are used to validate the pipeline inside the domain; they are broader than the original OpenWrt-only smoke test but still do not represent the full intended production corpus.

Raw third-party documents should not be committed unless redistribution rights are clearly verified. For Phase 2, source URLs and provenance are recorded in `sources.csv`; raw content is not copied into the repository.

## Structure

- `raw/`: local-only source documents, organized by category
- `processed/`: cleaned or normalized outputs produced by ingestion
- `sources.csv`: source metadata and provenance registry

## Production Collection Rules

- Keep sources inside the networking/router/connectivity support domain.
- Prefer official product manuals, setup guides, troubleshooting articles, firmware guidance, configuration docs, FAQs, technical references, and support policies.
- Do not add unrelated domains just to increase source count.
- Do not index marketing pages, link-list pages, old wiki indexes, or navigation-only pages as support evidence.
- Record provenance, product, version, language, category, retrieval date, license status, source type, and raw storage policy for every source.

## Current Registry Shape

- 21 official support sources
- Source families: OpenWrt, TP-Link, NETGEAR, ASUS
- Categories: setup, troubleshooting, configuration, firmware, manuals, faq
- Raw storage policy: URL/provenance only until redistribution rights are verified
