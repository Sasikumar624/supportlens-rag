# SupportLens Phase 2 Document Collection

Status: Stage B seed source registry complete; raw document downloads intentionally deferred until license handling is verified.
Date: 2026-09-29

## Objective

Phase 2 starts the knowledge-base collection process for the locked domain:

Networking, router, and connectivity support.

The detailed production domain contract is defined in [SupportLens Domain Specification](domain-specification.md). Phase 2 applies that contract to data collection: sources must be trusted, coherent, support-oriented, metadata-rich, and legally safe to reference or store.

The goal is not to ingest or chunk documents yet. The goal is to identify reliable support sources, record provenance, organize the dataset structure, and avoid committing third-party raw content without redistribution permission.

## Completed

- Created the dataset directory structure under `data/`.
- Added category folders under `data/raw/`.
- Added `data/processed/` for later ingestion outputs.
- Added `data/sources.csv` as the source provenance registry.
- Seeded 5 Stage A smoke-test sources from official OpenWrt documentation.
- Expanded the registry to 21 Stage B seed sources across official OpenWrt, TP-Link, NETGEAR, and ASUS support documentation.
- Recorded source URL, title, category, product, version, language, retrieval date, license status, notes, source type, and raw storage policy.
- Deferred raw content download because redistribution/license status has not yet been confirmed.

## Stage A Source Set

The initial smoke-test source set uses official OpenWrt documentation because it fits the project domain and includes setup, troubleshooting, reset/recovery, Wi-Fi configuration, and firmware-upgrade procedures.

OpenWrt is the Stage A seed product, not the full project domain. The broader domain remains networking, router, and connectivity support. Stage A intentionally starts with one coherent source family so the pipeline can validate ingestion, cleaning, metadata, retrieval, citations, no-answer behavior, and frontend UX before expanding to more products and source families.

| ID | Title | Category | URL |
| --- | --- | --- | --- |
| DOC001 | Quick start guide for OpenWrt installation | setup | https://openwrt.org/docs/guide-quick-start/start |
| DOC002 | Internet connectivity and troubleshooting | troubleshooting | https://openwrt.org/docs/guide-quick-start/checks_and_troubleshooting |
| DOC003 | Failsafe mode, factory reset, and recovery mode | troubleshooting | https://openwrt.org/docs/guide-user/troubleshooting/failsafe_and_factory_reset |
| DOC004 | Wi-Fi configuration | configuration | https://openwrt.org/docs/guide-user/network/wifi/start |
| DOC005 | Upgrading OpenWrt firmware using LuCI | firmware | https://openwrt.org/docs/guide-quick-start/sysupgrade.luci |

## Stage B Seed Source Set

The Stage B seed set broadens the corpus beyond OpenWrt while staying inside the same domain. The registry now includes 21 official sources across multiple product/vendor families.

| Source family | Products represented | Source count | Support coverage |
| --- | --- | ---: | --- |
| OpenWrt | OpenWrt firmware documentation | 9 | setup, troubleshooting, Wi-Fi, firmware, backup/restore, DHCP/DNS, firewall, project overview |
| TP-Link | Archer AX21, Archer AX55, TP-Link routers | 4 | user guide, firmware precautions, factory reset, internet troubleshooting |
| NETGEAR | NETGEAR routers | 4 | firmware update, factory reset, router access, Wi-Fi SSID/password configuration |
| ASUS | ASUS routers | 4 | factory reset, firmware update, rescue mode, hard factory reset |

The Stage B registry is intentionally source-family balanced enough to test multi-product behavior without mixing unrelated domains. All sources are official support, documentation, or FAQ pages. Raw content is not committed; the repository records URLs and provenance until redistribution terms are verified.

Representative Stage B additions:

| ID | Title | Category | Product |
| --- | --- | --- | --- |
| DOC006 | OpenWrt backup and restore | troubleshooting | OpenWrt |
| DOC007 | OpenWrt DHCP and DNS examples | configuration | OpenWrt |
| DOC008 | OpenWrt firewall configuration | configuration | OpenWrt |
| DOC009 | TP-Link Archer AX21 installation and user guide | manuals | TP-Link Archer AX21 |
| DOC010 | TP-Link Archer AX55 support download and firmware guidance | firmware | TP-Link Archer AX55 |
| DOC011 | TP-Link factory reset guidance | troubleshooting | TP-Link Routers |
| DOC012 | TP-Link router internet connectivity troubleshooting | troubleshooting | TP-Link Routers |
| DOC013 | NETGEAR router firmware update with web browser | firmware | NETGEAR Routers |
| DOC014 | NETGEAR router factory reset | troubleshooting | NETGEAR Routers |
| DOC015 | NETGEAR router access troubleshooting | troubleshooting | NETGEAR Routers |
| DOC016 | NETGEAR WiFi password or SSID change | configuration | NETGEAR Routers |
| DOC017 | ASUS router factory reset | troubleshooting | ASUS Routers |
| DOC018 | ASUS router firmware update via Web GUI | firmware | ASUS Routers |
| DOC019 | ASUS rescue mode firmware restoration | troubleshooting | ASUS Routers |
| DOC020 | ASUS hard factory reset model list | troubleshooting | ASUS Routers |
| DOC021 | About the OpenWrt project | faq | OpenWrt |

## Production Source Strategy

The final knowledge base should not be a random list of URLs. It should grow as a curated support corpus inside the locked domain.

Accepted source families:

- Official product manuals and user guides
- Quick-start and installation guides
- Firmware upgrade, release, and migration guidance
- Troubleshooting and recovery articles
- Wi-Fi, LAN, WAN, DHCP, DNS, firewall, and routing configuration docs
- FAQ/help-center articles
- Technical references for supported models, hardware revisions, firmware versions, and exact identifiers
- Warranty, support, maintenance, and service-policy documents

Rejected or deferred source families:

- Marketing pages with little support value
- Forum threads unless manually curated as support knowledge
- Link-list pages, table-of-contents pages, old wiki indexes, and page-navigation content
- Sources with unclear provenance or unstable URLs
- Third-party raw content whose redistribution rights are not verified
- Documents from unrelated domains added only to increase corpus size

## Dataset Expansion Plan

Stage A proves the pipeline with one coherent source family.

Stage B expands to about 20 sources while preserving domain coherence. The current registry reaches that first Stage B shape with OpenWrt, TP-Link, NETGEAR, and ASUS official support sources.

Stage C should reach 50-100 useful support sources and 2,000-6,000 indexed chunks. Production metrics should not be claimed until this broader corpus is evaluated for retrieval quality, answer quality, citation correctness, refusal behavior, multi-product behavior, and end-user clarity.

## Directory Structure

```text
data/
  raw/
    manuals/
    setup/
    troubleshooting/
    faq/
    configuration/
    policies/
    technical/
    firmware/
  processed/
  sources.csv
```

## License Policy

For Phase 2, raw source content is not committed to Git.

The repository records URLs and metadata only until each source's redistribution terms are confirmed. If a source cannot be redistributed, the project will keep:

- Source URL
- Metadata
- Collection notes
- Reproducible ingestion instructions

This follows the Phase 0 rule: do not blindly upload third-party copyrighted PDFs or copied documentation into GitHub.

## Next Step

Phase 3 should implement document loading. Because the Stage A sources are HTML pages rather than PDFs, Phase 3 can either:

1. Start with a PDF loader and collect 3-5 permissively redistributable PDFs, or
2. Add an HTML loader early and ingest the recorded OpenWrt pages from their URLs.

The cleaner path for this dataset is option 2: add an HTML loader after the basic loader abstraction exists.
