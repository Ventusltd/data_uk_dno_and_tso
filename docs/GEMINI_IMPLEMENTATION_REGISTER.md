# Gemini implementation register

This file records which parts of the Gemini report were implemented into repo code and which were rejected or deferred.

## Implemented as verified engineering value

### OpenDataSoft portal pattern

Implemented because the OpenDataSoft Explore API v2.1 pattern is materially useful for UKPN, SPEN, Electricity North West and Northern Powergrid style portals.

Repo implementation:

- `scripts/lib/opendatasoft.py`
- `scripts/fetch_ods_catalogue.py`
- `config/sources.json` entries for ODS portals

Engineering rule:

- use `/api/explore/v2.1/catalog/datasets` for catalogue discovery
- use `/records` only for bounded queries
- use `/exports/{format}` for bulk extraction
- expect `limit` caps and `offset + limit` caps on records queries
- support API key via environment variable where required

### NGED Connected Data token requirement

Implemented as source metadata only. No secret is committed.

Repo implementation:

- `config/sources.json` entry `nged_connected_data`
- `scripts/fetch_ckan_catalogue.py`

Engineering rule:

- token must be provided by environment variable or GitHub secret
- never commit API tokens
- CKAN fetchers must be rate-limited and audit-friendly

### SSEN correction

Implemented because Gemini incorrectly grouped SSEN with the OpenDataSoft family.

Repo implementation:

- `config/sources.json` entry `ssen_distribution_data_portal`
- `docs/PORTAL_ENGINEERING.md`

Engineering rule:

- SSEN Distribution is not treated as an ODS portal in this repo
- build a separate metadata/RDF/JSON-LD-aware fetcher later
- do not confuse SSEN Distribution with SSEN Transmission

### Declared-first and audit-first model

Implemented because it matches the repo design and avoids unverified data publication.

Repo implementation:

- declared seed CSVs
- validation script
- build script
- manual audit workflow

## Deferred pending official source verification

- exact UK network statistics
- exact ECR schemas per DNO
- LTDS/CIM dates and derogation details
- DFES per-operator table schemas
- TEC queue schema details
- Ireland redistribution status
- Braintree project-credit specifics

## Rejected from implementation

- poetic or philosophical claims as code facts
- any unverified live grid snapshot values
- any claim that network stats seed rows are verified publication data
- any claim that NESO owns transmission assets
- any claim that SSEN Distribution is an OpenDataSoft portal

## Coding principle

Only operationally useful, verifiable claims become code. Narrative claims may be documented separately but must not become machine truth.
