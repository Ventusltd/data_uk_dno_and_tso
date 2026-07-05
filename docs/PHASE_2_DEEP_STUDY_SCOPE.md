# Phase 2 deep study scope

This is the landing scope for the deeper study running in parallel with the phase 1 scaffold.

## Purpose

Move beyond the simple operator and licence-area layer into the hard operational datasets needed for atlas v8, SLD financial sandbox, BESS analysis, IDNO comparison, behind-the-meter intelligence and federation spiders.

## Study areas

### Portal mechanics

For each source, establish:

- platform type: OpenDataSoft, CKAN, static file, ArcGIS, bespoke API or PDF/manual source
- authentication requirement
- rate limits
- export formats
- stable dataset identifiers
- licence and attribution text
- pagination behaviour
- schema drift risk
- deterministic fetch strategy

### GB DNO open data portals

Cover at least:

- UK Power Networks
- National Grid Electricity Distribution
- SP Energy Networks
- Scottish and Southern Electricity Networks Distribution
- Northern Powergrid
- Electricity North West

### Deep dataset classes

Prioritise:

- embedded capacity registers
- network headroom
- substation capacity
- long-term development statements
- DFES forecasts
- flexibility market tenders and outcomes
- connection queues
- reinforcement plans
- network statistics derived from regulatory reporting
- geospatial licence and asset context where licensing permits

### NESO layer

Confirm the practical relationship between:

- NESO boundaries
- FES building blocks
- ETYS data
- regional demand/generation scenarios
- transmission owner areas
- distribution licence areas

### Ireland layer

Study licensing and mechanics for:

- NIE Networks
- SONI
- ESB Networks
- EirGrid
- NI Utility Regulator
- CRU

Default state is restricted until redistribution is explicitly cleared.

### Join layer

Define stable join keys for:

- MPAN distributor ID
- GSP group
- licence area
- operator ID
- regulator ID
- transmission owner/system operator bridge
- Irish jurisdictional equivalents where MPAN does not apply
- spatial joins from REPD/project coordinates to licence areas

## Output expected from study

The study should return:

- source-by-source API mechanics
- dataset priority table
- licence status table
- recommended fetcher order
- table schemas for deep operational datasets
- failure modes and audit checks
- downstream JSON/GeoJSON payload design for atlas and sandbox

## Constraint

Do not add unverified public data to this repo from the study. First add source records, schemas, fetcher stubs and licence status. Data ingestion follows only after audit gate passes.
