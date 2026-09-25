# SupportLens Phase 2 Document Collection

Status: Stage A source registry complete; raw document downloads intentionally deferred until license handling is verified.
Date: 2026-09-25

## Objective

Phase 2 starts the knowledge-base collection process for the locked domain:

Networking, router, and connectivity support.

The goal is not to ingest or chunk documents yet. The goal is to identify reliable support sources, record provenance, organize the dataset structure, and avoid committing third-party raw content without redistribution permission.

## Completed

- Created the dataset directory structure under `data/`.
- Added category folders under `data/raw/`.
- Added `data/processed/` for later ingestion outputs.
- Added `data/sources.csv` as the source provenance registry.
- Seeded 5 Stage A smoke-test sources from official OpenWrt documentation.
- Recorded source URL, title, category, product, version, language, retrieval date, license status, notes, source type, and raw storage policy.
- Deferred raw content download because redistribution/license status has not yet been confirmed.

## Stage A Source Set

The initial smoke-test source set uses official OpenWrt documentation because it fits the project domain and includes setup, troubleshooting, reset/recovery, Wi-Fi configuration, and firmware-upgrade procedures.

| ID | Title | Category | URL |
| --- | --- | --- | --- |
| DOC001 | Quick start guide for OpenWrt installation | setup | https://openwrt.org/docs/guide-quick-start/start |
| DOC002 | Internet connectivity and troubleshooting | troubleshooting | https://openwrt.org/docs/guide-quick-start/checks_and_troubleshooting |
| DOC003 | Failsafe mode, factory reset, and recovery mode | troubleshooting | https://openwrt.org/docs/guide-user/troubleshooting/failsafe_and_factory_reset |
| DOC004 | Wi-Fi configuration | configuration | https://openwrt.org/docs/guide-user/network/wifi/start |
| DOC005 | Upgrading OpenWrt firmware using LuCI | firmware | https://openwrt.org/docs/guide-quick-start/sysupgrade.luci |

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

