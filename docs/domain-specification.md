# SupportLens Domain Specification

Status: Authoritative domain definition for the current project
Date: 2026-09-29

## Domain Summary

SupportLens is a domain-specific RAG assistant for networking, router, and connectivity support.

The product is designed to help users answer practical technical-support questions from trusted documentation about customer networking equipment and connectivity workflows. The assistant should behave like a support knowledge-base layer for router setup, firmware maintenance, local network configuration, Wi-Fi configuration, connectivity troubleshooting, recovery procedures, and related product-support policies.

This project is not a general chatbot and is not a generic document Q&A demo. The system must answer only from indexed, trusted support documents and must refuse or qualify answers when the knowledge base does not provide enough evidence.

## Production Product Framing

In a production setting, SupportLens would sit between end users, support agents, and a company's technical-support knowledge base.

Primary value:

- Reduce time spent searching manuals, help articles, and support pages.
- Provide direct support answers with citations to trusted documents.
- Preserve source provenance so users can verify answers.
- Refuse unsupported questions instead of inventing product behavior.
- Support exact technical identifiers such as model numbers, IP addresses, firmware versions, and error codes.

Production users:

- Home or small-office router users who need clear setup and troubleshooting guidance.
- Tier-1 support agents who need fast, cited answers during customer conversations.
- Network administrators who need quick references for firmware, Wi-Fi, LAN/WAN, and recovery tasks.
- QA or documentation teams evaluating whether support content answers common user questions.

## User Intent Scope

In-scope user intents:

- Install or set up a router or network device.
- Check whether a device or firmware path is supported.
- Configure Wi-Fi, LAN, WAN, DHCP, DNS, or access settings.
- Troubleshoot no-internet, unstable Wi-Fi, DHCP failures, access loss, or post-upgrade issues.
- Recover access using failsafe, reset, or recovery procedures.
- Upgrade firmware safely and understand pre-upgrade precautions.
- Interpret documented error codes, model identifiers, versions, or configuration terms.
- Locate the right support document or cited evidence.
- Understand warranty, support, or maintenance policies when those documents are indexed.

Out-of-scope user intents:

- Medical, legal, financial, vehicle, or unrelated consumer-electronics advice.
- General programming help unrelated to the indexed networking support documents.
- Product claims not supported by indexed documentation.
- Live network diagnosis requiring device telemetry the system does not have.
- Security exploitation, credential bypass, or unsafe device access guidance.
- Purchasing recommendations unless supported product-selection documents are indexed.

## Knowledge-Base Scope

The production knowledge base should include a coherent set of networking support sources, not isolated sample pages.

Target source families:

- Product manuals and user guides.
- Quick-start and installation guides.
- Firmware upgrade and release guidance.
- Troubleshooting articles and recovery procedures.
- Wi-Fi, LAN, WAN, DHCP, DNS, firewall, and routing configuration docs.
- FAQ/help-center articles.
- Technical reference pages for supported models, firmware versions, and hardware revisions.
- Warranty, support, and maintenance policy documents.
- Known-issue, release-note, or migration guidance where available.

Target product families:

- Consumer and small-office routers.
- Open-source router firmware distributions.
- Access points and mesh networking devices.
- Modems, gateways, and edge connectivity devices where documentation fits the same support workflow.

The repository started with OpenWrt documentation as the Stage A seed product because it fits the locked domain and provides real installation, firmware, Wi-Fi, troubleshooting, reset, and recovery documentation. The source registry has now been expanded into a Stage B seed set with multiple official source families: OpenWrt, TP-Link, NETGEAR, and ASUS. OpenWrt is not the full domain; it is one source family inside the broader networking/router/connectivity support domain.

## Source Quality Requirements

Each source must be evaluated before indexing.

Accepted source qualities:

- Official vendor, project, or product documentation.
- Stable source URL and identifiable document title.
- Clear product, version, language, category, and retrieval date.
- Documentation content that directly supports user troubleshooting or setup tasks.
- License or redistribution status recorded before raw content is committed.

Rejected or deferred source qualities:

- Marketing pages with little support value.
- Forum discussions unless explicitly curated as support knowledge.
- Duplicated navigation pages, link lists, old wiki indexes, or table-of-contents pages.
- Raw copied third-party content without license review.
- Documents from unrelated domains added only to increase volume.

## Required Metadata

Every indexed document or chunk must preserve metadata that can support retrieval, filtering, citations, evaluation, and operational debugging.

Required document metadata:

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
- `source_type`
- `raw_storage_policy`

Required chunk metadata:

- `chunk_id`
- `document_id`
- `title`
- `category`
- `product`
- `version`
- `language`
- `source_url`
- `source_type`
- `page` when available
- `section` when available
- `text`
- `token_count`
- `block_ids`
- `block_types`

## Category Taxonomy

The project uses these support categories as the first production taxonomy:

| Category | Purpose | Example user questions |
| --- | --- | --- |
| `setup` | Installation, onboarding, first-use guidance | "How do I install this firmware on my router?" |
| `troubleshooting` | Diagnosis and recovery for broken or unexpected behavior | "Why did internet stop working after an upgrade?" |
| `configuration` | Feature and network setting configuration | "How do I configure Wi-Fi or DHCP?" |
| `firmware` | Upgrade, sysupgrade, release, and image handling | "What should I check before flashing firmware?" |
| `faq` | Short product-support answers and common issues | "What does this support term mean?" |
| `manuals` | Long-form product manuals and user guides | "Where is the documented reset procedure?" |
| `technical` | Reference material, exact identifiers, compatibility, specs | "Which model or hardware revision is supported?" |
| `policies` | Warranty, support, maintenance, and service boundaries | "Is this issue covered by support?" |

## Expected Answer Contract

A production answer should:

- Directly answer the user's support question in plain language.
- Prefer short, actionable steps for procedural questions.
- Include inline citations that map to returned source cards.
- Mention important warnings or prerequisites when the source includes them.
- Say when the available documentation is incomplete.
- Avoid exposing retrieval metadata, raw chunk IDs, page chrome, table-of-contents text, or source-navigation noise as answer content.

The frontend should present source evidence as a verification layer, not as the answer itself.

## Evaluation Coverage

The final evaluation dataset must represent the domain, not only one product page.

Required evaluation groups:

- Installation and first-time setup questions.
- Firmware upgrade and rollback-safety questions.
- Connectivity troubleshooting questions.
- Wi-Fi and LAN/WAN configuration questions.
- Reset, recovery, and failsafe questions.
- Exact model, firmware, IP address, or error-code questions.
- Multi-document questions where the answer requires more than one source.
- Ambiguous questions that require refusal or clarification.
- Out-of-domain questions that must be refused.

Production readiness should be measured with retrieval quality, answer quality, citation correctness, refusal behavior, and manual review of user-facing clarity.

## Current Stage B Seed Corpus

The current source registry contains 21 official support sources. It is still a seed corpus, but it is no longer limited to a single product family.

Current source families:

- OpenWrt
- TP-Link router support
- NETGEAR router support
- ASUS router support

Current source types:

- Official project documentation pages
- Official vendor support pages
- Official vendor FAQ/help articles
- Official vendor product/user-guide pages

Current categories:

- `setup`
- `troubleshooting`
- `configuration`
- `firmware`
- `manuals`

Current limitation:

- The corpus is broader than the original OpenWrt-only smoke test, but it is still not large enough to claim full production coverage across networking products. It is a realistic Stage B seed set for validating ingestion, cleaning, retrieval, answer generation, citations, no-answer behavior, definitional FAQ answers, multi-product source filtering, and UI behavior inside the locked domain.

## Expansion Plan

Stage B expands from the OpenWrt seed set to about 20 coherent support documents across the same domain. The current registry has reached this initial Stage B shape.

Recommended next Stage B additions:

- More OpenWrt official docs for installation, supported devices, network interfaces, firewall, DHCP/DNS, wireless security, backup/restore, and upgrade paths.
- More vendor-specific setup and troubleshooting documents from the currently selected TP-Link, NETGEAR, and ASUS source families.
- A small set of policy or warranty/support pages to exercise non-procedural support answers.
- A reviewed set of product-manual PDFs only after local PDF fetching/storage and redistribution policy are handled correctly.

Stage C should reach 50-100 useful sources and 2,000-6,000 indexed chunks before production-quality metrics are claimed.

Expansion must preserve domain coherence. Do not add unrelated documents just to increase document count.

## UI Implications

End users should see SupportLens as a support assistant, not as a backend retrieval console.

The default UI should:

- Lead with a natural-language question box.
- Show example questions based on real support intents.
- Hide advanced metadata filters unless the user chooses to narrow sources.
- Present answers first and citations second.
- Use evidence/source panels for verification, not as the primary reading experience.
- Avoid labels such as backend, chunk, payload, source type, or document ID in the primary user path.

Debug-oriented retrieval details may exist in separate admin or developer views, but should not dominate the normal user experience.
