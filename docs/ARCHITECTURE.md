# Architecture

## Repository role

`data_uk_dno_and_tso` is the canonical data spine for UK and Ireland electricity network authorities and public network context.

It separates:

- declared entity data
- fetched public source data
- derived analytical data
- renderer-ready JSON and GeoJSON

## Layering

```text
data/declared/        Small human-maintained seed tables
data/raw/             Source snapshots, only where licence permits
build/parquet/        Generated analytical truth tables
build/json/           Compact renderer payloads
build/geojson/        Compact renderer overlays
audit/                Receipts for every deterministic run
```

## Entity model

The load-bearing distinction is operator versus owner.

- DNO: licensed geographic distribution network operator
- IDNO: licensed non-geographic independent distribution network operator
- TO: transmission owner
- SO: system operator
- DSO: distribution-system role where a source explicitly uses that term

NESO is modelled as a system operator, not a transmission owner. NGET, SPT and SSEN Transmission are modelled separately as transmission owners.

## Core tables

```text
operators
mpan_distributor
transmission_ownership
department_lineage
licence_areas
network_stats
source_registry
```

## Data movement

```text
config/sources.json
  -> scripts/fetch_*.py
  -> data/raw/ where legally permitted
  -> build/parquet/
  -> build/json/ and build/geojson/
  -> atlas, sandbox, spiders and downstream repos
```

## Parquet and DuckDB rule

Small entity tables are single unpartitioned Parquet files.

Time-varying statistics are Hive partitioned by stable dimensions such as:

```text
operator=<operator_id>/year=<yyyy>/data.parquet
```

DuckDB reads the partitioned files with `hive_partitioning=true`. DuckDB spatial can build derived GeoJSON overlays, but renderer applications must not query DuckDB directly.

## Provenance rule

Every data row must carry:

```text
schemaVersion
methodState
source
provenance
retrieved_at
```

Allowed provenance values are:

```text
declared
derived
fetched
restricted
```

## First build scope

Phase 1 is declared-only. It creates the table contracts and seed records needed to reason about UK and Ireland network authorities without fetching or redistributing restricted source data.
