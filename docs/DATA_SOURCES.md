# Data sources

This document explains the source classes. The machine-readable registry is `config/sources.json`.

## Source classes

```text
neso              NESO portal and public datasets
ofgem             Ofgem licence and RIIO data
uk_government     UK government public energy datasets
dno_portal        DNO open-data portals
ireland           Ireland and Northern Ireland network sources
internal_declared Human-maintained seed records with source notes
```

## Priority sources

- NESO DNO licence-area boundaries
- Ofgem licence register
- Ofgem RIIO-ED2 and RIGs packs
- DNO open-data portals
- UK government public energy datasets
- Northern Ireland Utility Regulator datasets
- CRU public datasets
- ESB Networks, EirGrid, SONI and NIE Networks datasets where licensing permits

## Licensing rule

Each source entry must record:

```text
licence
attribution
redistribution_state
methodState
candidate_urls
```

Allowed redistribution states:

```text
open
check_terms
restricted
not_redistributed
```

Ireland sources default to `check_terms` or `restricted` until the licence is explicitly confirmed.

## Naming rule

Government datasets are stored under `uk_government_public_data`, not under the current department name. The publishing department is recorded as data in `department_lineage` and in row metadata.
