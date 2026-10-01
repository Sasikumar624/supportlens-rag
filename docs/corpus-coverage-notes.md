# Corpus Coverage Notes

Status: Stage B+ source expansion completed
Date: 2026-10-01

SupportLens is scoped to networking, router, and connectivity support. The source registry now includes 45 official sources across OpenWrt, TP-Link, NETGEAR, and ASUS.

## Added Coverage

- Product specifications for TP-Link Archer AX21, TP-Link Archer AX55, and ASUS RT-AX55.
- First-time setup and router-login guidance for TP-Link, NETGEAR, and ASUS.
- Wi-Fi settings and WAN/LAN configuration guidance.
- LED/status troubleshooting for NETGEAR.
- Warranty/RMA and regulatory policy-style sources.
- OpenWrt supported-device, Table of Hardware, IPv4, network configuration, Wi-Fi setup, country-code, and generic sysupgrade references.

## Still Intentionally Not Covered

Live/current pricing is not safe to answer from static support documentation. To support price-range answers, add a separate pricing feed with:

- product/model identifier
- source URL
- region
- currency
- observed price
- retrieval timestamp
- validity/expiration timestamp when known
- scheduled refresh and stale-data refusal behavior

Until that exists, pricing questions should be refused or qualified instead of answered from stale support text.

## Next Production Step

After re-indexing, run retrieval and answer-quality evaluation against setup, specifications, firmware, troubleshooting, warranty, regulatory, and unanswerable pricing questions. Treat any unsupported answer as a RAG/no-answer failure, not as an acceptable LLM variation.
