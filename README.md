# data_uk_dno_and_tso

Declared and derived public-data spine for UK and Ireland electricity network operators, licence areas, regulators, government energy datasets, NESO, transmission owners, DNOs, IDNOs and Irish equivalents.

This is a data repository, not an application repository.

## Purpose

This repo establishes the canonical operator and network-area layer that can feed:

- atlas v8 overlays
- SLD financial sandbox context panels
- UK energy generation history
- federation spiders
- battery storage repositories
- IDNO and DNO comparisons
- behind-the-meter datasets
- future energy-company repositories

## Design principle

Heavy truth lives as Parquet. DuckDB is the query engine. Renderers consume only compact derived JSON or GeoJSON.

The first build is deliberately simple and declared-only. It must not pretend to be a live automated data feed until fetchers, licences, hashes and audit receipts are proven.

## Core folders

```text
config/                         Source registry
schemas/                        JSON schemas for table contracts
scripts/                        Deterministic build, fetch and validation scripts
scripts/lib/                    Shared provenance, hashing and IO helpers
data/declared/                  Human-maintained seed inputs
build/                          Generated Parquet, JSON and GeoJSON outputs
archive/                        Future frozen source snapshots, if legally permitted
audit/                          Markdown and JSON run receipts
docs/                           Architecture, definitions, sources and changelog
.github/workflows/              Manual workflows first; cron only after idempotence
```

## First milestone

Phase 1 creates:

- operators
- MPAN distributor lookup
- transmission ownership bridge
- department lineage
- source registry
- schema contracts
- validation/audit scripts

No live fetcher is enabled by default. Data becomes publishable only after the audit gate passes.

## Audit gate

A run is acceptable only when:

- clean clone works with no manual edits
- every row has provenance fields
- every source has licence and attribution metadata
- generated outputs are deterministic
- SHA-256 hashes are recorded in audit receipts
- renderer files are compact derived JSON or GeoJSON
