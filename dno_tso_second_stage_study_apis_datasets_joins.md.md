# Second-Stage Engineering Study — `Ventusltd/data_uk_dno_and_tso`

## Deep Operational Layers for UK & Ireland Network-Operator Data

## TL;DR

- Build fetchers around **three API families**: **Opendatasoft Explore v2.1** (UKPN, SPEN, ENWL, Northern Powergrid, SSEN Transmission), **CKAN Action API v3** (NGED/ex-WPD `connecteddata.nationalgrid.co.uk`, NESO `api.neso.energy`), and **plain-file/portal downloads** (SSEN Distribution, ESB Networks, EirGrid, SONI, NIE). The Opendatasoft `/records` endpoint is capped at **100 rows** with **offset+limit ≤ 10,000**, so all bulk pulls MUST use `/exports` (uncapped); CKAN pulls should use `datastore_search`/`datastore_search_sql` respecting NESO’s guidance (“CKAN API: … maximum one request per second. Datastore API: … maximum of two requests per minute” — NESO API guidance).
- The high-value deep datasets are the **Embedded Capacity Register** (DCUSA-mandated, ENA-standard, ≥1MW plus the 50kW–1MW tier; “Within 10 Working Days following the end of each month, each DNO and IDNO will publish on their websites an updated ECR”), **LTDS** (migrating to CIM + Capacity Heatmap under Ofgem’s 30 Apr 2024 direction, with DNO deliverables deferred — per Ofgem’s Nov 2024 LTDS CIM Derogation Letter, Stage 2 and Stage 3 have “amended publication dates of 29 May 2026 and 30 November 2026 respectively”), **DFES/NDP headroom**, **flexibility tenders**, and the **NESO TEC/Interconnector/Embedded registers** (twice-weekly). These feed the atlas overlay, BESS siting screening, and the pipeline dashboard respectively.
- Ireland is a mixed-openness picture: ESB Networks capacity heatmap and EirGrid connected/contracted generator lists are published but largely as interactive maps/PDF/Excel (not clean APIs); mark them **degraded** in the registry. Join GB↔all-island via interconnector edges — per EPEX SPOT (10 Feb 2025), “Moyle (in commercial operation since 2002, offering 500MW) and EWIC (in commercial operation since 2012, offering 500MW)”  plus Greenlink (commercial operation 29 Jan 2025, first delivery day 30 Jan 2025), so “the available interconnection capacity totals 1500MW on the SEM-GB border”  — and honour the MPAN (GB, distributor IDs 10–23) vs MPRN (Ireland, 11-digit, prefix 10) numbering split.

## Key Findings

1. **Portal API families are only three.** Six of the eight GB DNO surfaces are either Opendatasoft or CKAN, so two reusable fetcher classes cover nearly everything. Only SSEN Distribution and the Irish/NI bodies need bespoke file handling.
1. **The `/records` vs `/exports` distinction is the single most important engineering fact for Opendatasoft.** Paginating `/records` past 10,000 rows is impossible; deterministic full pulls require `/exports/csv` or `/exports/parquet` with `order_by` for stable ordering.
1. **The ECR is a genuinely standardised, cross-DNO dataset** (DCUSA Schedule 31, Clause 35C of Section 2A; standardised via the DCP350 modification that renamed and extended the earlier System Wide Resource Register to ≥50kW), published monthly, making it the backbone for BESS/generation screening across all of GB.
1. **LTDS is mid-reform**: the tabular Excel form persists while CIM (CGMES-based) EQ profiles and Capacity Heatmaps are phased in. Per BSI (cim.bsigroup.com), “Ofgem has developed the use of CIM as a data model using an existing standard known as the Common Grid Model Exchange Standard (CGMES),”  with governance under a “GB CIM Governance Structure led by BSI.” Design for both formats.
1. **NESO connections data is the transmission-side spine** (TEC Register, Interconnector Register, Embedded Register for Scotland), updated twice weekly, now carrying a Gate 1/Gate 2 column from the TMO4+ connections reform.
1. **Ireland is real but gated/unstructured** — treat ESB Networks, EirGrid, SONI, NIE as screening-grade, honestly flagged.

## Details

### Layer 1 — Per-Portal API Reference & Fetcher Engineering

#### Portal reference table

|Portal                                         |Domain                               |API family               |Auth                                                                 |Bulk export                                                         |Licence                                                   |Key limits                                                                   |
|-----------------------------------------------|-------------------------------------|-------------------------|---------------------------------------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------|-----------------------------------------------------------------------------|
|UK Power Networks                              |ukpowernetworks.opendatasoft.com     |Opendatasoft Explore v2.1|None for open data (some tables registration-gated); optional API key|`/exports/{csv,json,geojson,parquet,xlsx}`                          |Creative Commons (CC BY 4.0 for data triages)             |`/records` max 100, offset+limit ≤ 10,000; quotas per-day, reset midnight UTC|
|National Grid Electricity Distribution (ex-WPD)|connecteddata.nationalgrid.co.uk     |CKAN Action API v3       |Optional API token (Authorization header)                            |`datastore_search`, `datastore_search_sql`, direct `/download/*.csv`|Presumed Open (CKAN)                                      |CKAN ~1 req/sec; datastore ~2 req/min                                        |
|SP Energy Networks                             |spenergynetworks.opendatasoft.com    |Opendatasoft Explore v2.1|None/optional key                                                    |`/exports/*`                                                        |SP Energy Networks Open Data Licence + Shared Data Licence|same ODS limits                                                              |
|SSEN Distribution                              |data.ssen.co.uk                      |Portal/file (bespoke)    |None                                                                 |Direct file downloads (ECR, LTDS, flex)                             |CC BY 4.0                                                 |n/a                                                                          |
|SSEN Transmission                              |ssentransmission.opendatasoft.com    |Opendatasoft Explore v2.1|None/optional key                                                    |`/exports/*`                                                        |CC BY 4.0                                                 |same ODS limits                                                              |
|Electricity North West                         |electricitynorthwest.opendatasoft.com|Opendatasoft Explore v2.1|None/optional key                                                    |`/exports/*`                                                        |CC BY 4.0                                                 |same ODS limits                                                              |
|Northern Powergrid                             |northernpowergrid.opendatasoft.com   |Opendatasoft Explore v2.1|Registration gives increased API count                               |`/exports/*`                                                        |Northern Powergrid Open Data Licence (OGL-style)          |same ODS limits                                                              |
|NESO                                           |data.neso.energy / api.neso.energy   |CKAN Action API v3       |None (optional)                                                      |`datastore_search`, `datapackage_show`, direct download             |Per-dataset licence                                       |datastore ≤ 2 req/min recommended                                            |
|ENA                                            |energynetworks.org                   |Web pages + linked files |None                                                                 |PDF/XLSX documents                                                  |ENA terms                                                 |n/a                                                                          |

**Opendatasoft Explore v2.1 mechanics.** Base path `https://<domain>/api/explore/v2.1`. Catalog: `/catalog/datasets` (dataset list, Dublin Core metadata via `domain-dataset0`/`metadata-catalogue`); per dataset: `/catalog/datasets/{dataset_id}/records` and `/catalog/datasets/{dataset_id}/exports/{format}`. The `/records` endpoint supports ODSQL: `select`, `where`, `group_by`, `order_by`, `limit`, `offset`. Per the official reference doc, “While the `records` endpoint is subject to a limited number of returned records, the `exports` endpoint has no limitations”; the concrete caps are **100 records per call and offset+limit ≤ 10,000** (the API returns `Invalid value for sum of offset + limit API parameter … <= 10000 is expected`). With a `group_by`, `total_count` caps at 20,000 groups. Authentication: API key via the `Authorization` header or `apikey` query parameter (OAuth2 also supported); not required for open datasets. Quotas are per-domain, delivered via `X-RateLimit-Limit`/`X-RateLimit-Remaining`/`X-RateLimit-Reset` headers and reset daily at midnight UTC; authenticated users get extended quotas over anonymous. Formats offered typically include CSV, JSON, GeoJSON, Parquet, XLSX. Each dataset exposes `modified`/metadata via the catalog record and a per-dataset Metadata (JSON) download.

**CKAN Action API mechanics.** Base `https://<domain>/api/3/action/`. Discovery: `package_list`, `package_show?id={slug}`, `resource_show?id={uuid}`. Data: `datastore_search?resource_id={uuid}&limit=&offset=` and `datastore_search_sql?sql=` (PostgreSQL engine, field IDs in double quotes). NESO also exposes `datapackage_show?id={dataset}`. NESO guidance verbatim: “CKAN API: It is recommended to limit requests to a maximum one request per second. Datastore API: … we recommend limiting requests to a maximum of two requests per minute,” and NESO “reserve the right to block that IP address” for overloading; avoid frequent polling to detect change. NGED (ex-WPD) issues optional API tokens passed via the `Authorization` header. Both expose per-resource `last_modified` and dataset `metadata_modified`.

**Deterministic fetcher pattern — Opendatasoft family (pseudocode):**

```
def fetch_ods(domain, dataset_id, schema_version, method_state):
    meta = GET f"{domain}/api/explore/v2.1/catalog/datasets/{dataset_id}"
    dataset_modified = meta.metadata.default.modified   # record for provenance
    # deterministic full pull — never /records for bulk
    url = f"{domain}/api/explore/v2.1/catalog/datasets/{dataset_id}/exports/parquet"
    params = {"order_by": "<stable_key> asc"}            # stable ordering
    raw = GET(url, params); sha = sha256(raw)
    cols = detect_columns(raw)
    assert_schema(cols, expected_map[dataset_id][schema_version])  # fail loud → degraded
    for row in raw:
        row.schemaVersion = schema_version
        row.methodState   = method_state
        row.provenance    = {"portal": domain, "dataset": dataset_id,
                             "dataset_modified": dataset_modified,
                             "fetched_at": now_utc(), "source_sha256": sha}
    write_parquet(hive_partition(dataset_id, dataset_modified))
    write_receipt({"sha256": sha, "rows": n, "dataset_modified": dataset_modified})
```

**Deterministic fetcher pattern — CKAN family (pseudocode):**

```
def fetch_ckan(base, dataset_slug):
    pkg = GET f"{base}/api/3/action/package_show?id={dataset_slug}"
    for res in pkg.result.resources:
        mod = res.last_modified or res.created           # provenance stamp
        if res.datastore_active:
            rows=[]; offset=0
            while True:
                page = GET f"{base}/api/3/action/datastore_search" \
                       f"?resource_id={res.id}&limit=1000&offset={offset}"
                rows += page.result.records
                if len(page.result.records) < 1000: break
                offset += 1000; sleep(30)               # ~2 req/min (NESO)
        else:
            raw = GET(res.url); rows = parse(raw)         # direct file
        sha = sha256(rows)
        assert_schema(columns(rows), expected_map[dataset_slug])
        stamp_and_write(rows, provenance={"resource_id":res.id,"last_modified":mod,"sha256":sha})
```

**Plain-file family:** fetch fixed URL, SHA-256 the bytes, compare to prior receipt; only re-ingest on hash change; parse Excel/CSV with an explicit column-mapping config per known layout version.

**Schema-drift detection:** persist a per-dataset `expected_columns` map keyed by `schemaVersion`. On each run, compute the actual column set; if it differs, fail loudly, write a `degraded` marker into the sources registry, and keep serving the last-good partition rather than ingesting mismatched columns. Record `dataset_modified`/`last_modified` from each portal every run so cron can skip unchanged datasets.

#### Deterministic pagination

Opendatasoft: never page `/records` beyond 10k — use `/exports` with a fixed `order_by` for reproducible byte output. CKAN: page `datastore_search` by fixed `limit`/`offset` with an `ORDER BY` in `datastore_search_sql` to guarantee stable order across runs.

### Layer 2 — Deep Network Datasets

**Embedded Capacity Register (ECR).** DCUSA-mandated (Section 2A Clause 35C, Schedule 31): “Within 10 Working Days following the end of each month, each DNO and IDNO will publish on their websites an updated ECR using the latest available information it holds as at the end of that month.” Standardised through the DCP350 modification (which renamed and extended the earlier System Wide Resource Register in July 2020 to cover ≥50kW). Standard content: customer name, project location, connection substation, POC voltage, registered/import/export capacity, technology type, connection status, flexibility services. Two tiers: ≥1MW (mandatory) and 50kW–1MW  (extended; ENWL was first DNO to publish the 50kW tier). ENA Open Networks agreed the format, so cross-DNO joins are viable (with the caveat DNOs warn cells may be unpopulated and POC is not exact). Slugs: UKPN `ukpn-embedded-capacity-register` (≥1MW) and `ukpn-embedded-capacity-register-1-under-1mw`; Northern Powergrid `embedded-capacity-register`; SPEN/ENWL/SSEN host equivalents. Feeds: BESS siting screening + pipeline dashboard + spider_maya nodes.

**LTDS + CIM + Capacity Heatmap.** Licence-condition (SLC25) network data: substation firm capacity, demand, fault levels. Ofgem’s direction of 30 Apr 2024 added CIM grid-model data (“Ofgem has developed the use of CIM as a data model using an existing standard known as the Common Grid Model Exchange Standard (CGMES),” per BSI) and mandatory Capacity Heatmaps. Per Ofgem’s Nov 2024 LTDS CIM Derogation Letter, a one-year extension applies to Table 7 stages: Stage 1.3 → 28 Nov 2025, with Stage 2 and Stage 3 given “amended publication dates of 29 May 2026 and 30 November 2026 respectively,”  and the Capacity Heatmap ~29 May 2026. Tabular Excel is retained alongside CIM (strong stakeholder demand to keep spreadsheets for non-experts). Updated each May and November.  CIM EQ profile covers 132kV (EHV in Scotland) down to 11kV primary busbars.  UKPN slug `ukpn-ltds-cim`; NGED `ltds-common-information-model` (per-licence-area zip downloads). Technical artefacts now on the BSI Engagement Hub (moved from the ENA Technical CIM Working Group GitHub — hard-coded artefact URLs will break). Feeds: atlas substation attributes + BESS headroom screening.

**Network capacity/headroom maps.** NGED capacity map + ClearViewConnect (headroom + connections pipeline at GSPs); UKPN `ukpn-grid-supply-points-overview` (GSP import/export limits for winter/summer/access, RAG technical limits agreed with NESO, asset import/export limits from supergrid transformer capacities), `ukpn_primary_postcode_area` and `ukpn-grid-postcode-area` (substation feed polygons derived from MPAN data + LTDS Table 3a firm capacity/season-of-constraint/%-unutilised), `dfes-network-headroom-report`. NIE Networks capacity map (RAG demand/generation/fault-level; a 2026 upgrade now integrates SONI transmission generation headroom at each BSP). Feeds: atlas overlays + BESS screening.

**DFES / NDP.** All DNOs publish annually, framework aligned with NESO FES. NGED CKAN dataset `dfes` (profiles, energy projections, power projections, annual scaling, volume projections by LA/ESA — ~2 million records, interactive map, CSV/PDF export). Northern Powergrid portal DFES datasets at BSP/GSP/LA/whole-network granularity (`northern-powergrid-dfes-wholearea`). UKPN `dfes-network-headroom-report` (DFES NSHR, part of NDP; 1 May 2025 dataset uses LTDS Nov 2024 loading as baseline + DFES 2025 scenarios; updated annually, biennial full NDP; indicative unused headroom at BSP/primary to 2050).  Feeds: pipeline dashboard scenario context.

**Flexibility markets.** ENA Open Networks tracks tendered vs contracted MW annually, aligned to DNO flexibility statements (SLC31E); markets grew from 117MW (2018) to 3.7GW tendered (2021). Platforms: Piclo Flex/Max, ElectronConnect, Flexible Power; a common framework agreement + standard asset data now removes the need for a separate PQQ. NGED “Flexibility Market Insights” dashboard; ENWL flex requirements on its Open Data Portal (Autumn tenders incl. LV requirements — e.g. Autumn 2025 procuring 280 LV requirements across 140 locations); SPEN, NPg publish tender/procurement data (NPg adopted Piclo Flex alongside Flexible Power). Feeds: BESS revenue-stacking context + pipeline dashboard.

**Connection queues / NESO registers.** TEC Register (`transmission-entry-capacity-tec-register`, “updated twice weekly on Tuesdays and Fridays”, now with a Gate 1/Gate 2 column added from 21 Nov 2025 following CUSC 6.30.3.2/6.35.2 post-TMO4+; note aggregate capacity may yield duplicate stage/technology entries pending refinement). Interconnector Register (Moyle, EWIC, Greenlink etc.; Moyle 500MW TEC subject to operational restrictions). Embedded Register (connected/contracted embedded generation in Scotland). All DNOs + NESO delivered digital connections-queue views in 2024 (per Ofgem’s connections end-to-end review). Access via CKAN `datapackage_show?id=transmission-entry-capacity-tec-register`. Feeds: pipeline dashboard + spider_maya.

**Substation datasets for atlas join.** UKPN GSP overview + GSP area polygons (`ukpn-grid-supply-points`, transmission sites feeding primaries), primary/grid postcode feed areas; NGED spatial datasets (Electricity Supply Areas incl. GSP/BSP/primary), 66kV pole-mounted substations shapefiles chunked on OS 20km grid. Feeds: atlas topology + point-in-polygon assignment.

### Layer 3 — Ireland Deep Pass (honest openness marking)

|Body        |Role                                 |What’s published                                                                                                                                                                                                   |Openness                                                                                               |
|------------|-------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
|ESB Networks|DSO (all-Ireland RoI; sole Irish DSO)|Availability Capacity Heatmap (LV/MV/HV substations, transformer capacity at 110kV/38kV/MV); Network Scenario Headroom Report (Demand workbook 2025; Generation due Q1 2026); Distribution Network Development Plan|Interactive map + Excel workbooks — **degraded** (no clean API)                                        |
|EirGrid     |TSO (RoI)                            |Connected & Contracted Generators lists; Smart Grid Dashboard (system demand, fuel mix, SNSP post-2022, wind), 15-min/5-sec series                                                                                 |PDF/Excel lists + dashboard endpoints (unofficial JSON, community scripts exist) — **degraded/partial**|
|SONI        |TSO (NI)                             |Transmission grid data, system/renewable data, generation headroom (now feeding NIE capacity map)                                                                                                                  |Web/PDF — **degraded**                                                                                 |
|NIE Networks|TO + DSO (NI)                        |Network Capacity Map (RAG demand/generation/fault; BSP transmission headroom from SONI as of 2026; “Bulk” = 110/33kV, “Primary” = 33/11kV & 33/6.6kV); Open Data Portal                                            |Interactive map — **degraded**; portal nascent                                                         |
|SEMO/SEMOpx |All-island market operator (SEM)     |SEM market data, interconnector intraday auctions (IDA1/IDA2)                                                                                                                                                      |Market data (some registration) — **partial**                                                          |
|CRU / UREGNI|Regulators (RoI / NI)                |Decisions (e.g. ECP-GSS process, ICC cap), guidance                                                                                                                                                                |PDF — reference only                                                                                   |

**Join to GB model:** interconnectors as graph edges — Moyle (500 MW, NI↔Scotland, Ballycronan More↔Auchencrosh, Mutual Energy, in service since 2001/ 2002), EWIC (500 MW, RoI↔Wales, Portan↔Shotton, EirGrid,  since 2012), Greenlink (504 MW nameplate / 500 MW rating, RoI↔Wales, Great Island↔Pembroke, ±320 kV symmetrical monopole, 200 km;  per EPEX SPOT “successful operational and commercial delivery … for delivery date 30th January 2025”).  Per EPEX SPOT the three together mean “the available interconnection capacity totals 1500MW on the SEM-GB border”; Celtic (700 MW, RoI↔France) is expected ~2027/28. Numbering: GB MPAN 13-digit core = 2-digit distributor ID (10–23) + 8-digit unique + 2 + check digit; Northern Ireland and RoI use MPRN, an 11-digit number starting “10” (per Electric Ireland). DSO/TSO split: GB = NESO (system operator) vs NGET/SP Transmission/SSEN Transmission (owners); Ireland = EirGrid/SONI (TSOs) + ESB Networks/NIE Networks (DSOs). Mark every gated Irish source as `declared: external, state: degraded` in the registry rather than implying full coverage.

### Layer 4 — Join Layer & Serving Patterns

**DuckDB spatial joins.** `INSTALL spatial; LOAD spatial;` Read boundaries: `ST_Read('licence_areas.geojson')` (GDAL-backed) → convert `wkb_geometry` via `ST_GeomFromWKB`. Assign points to areas:

```sql
SELECT p.id, a.licence_area
FROM points p JOIN areas a
ON ST_Contains(a.geom, ST_Point(p.lon, p.lat));
```

CRS: REPD and OS data are EPSG:27700; convert with `ST_Transform(geom,'EPSG:27700','EPSG:4326')` (or `'OGC:CRS84'`) before joining to WGS84 GeoJSON; store/serve in EPSG:4326 per RFC 7946 (which mandates WGS84 longitude/latitude order). For ~3000 REPD points against 14 polygons the join is sub-second; a bounding-box pre-filter (`ST_Intersects` on `ST_Envelope`) and converting WKB→GEOMETRY once at load avoid repeated blob decode. Export derived GeoJSON with `COPY area_summary TO 'licence_areas.geojson' WITH (FORMAT GDAL, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES', SRS 'EPSG:4326')`.

**Derived artefact schemas (compact, per consumer):**

- *Atlas overlay* — `licence_areas.geojson` (RFC 7946 FeatureCollection): each Feature = licence-area polygon + properties `{operator, distributor_id, ecr_mw_connected, ecr_mw_accepted, gsp_count, headroom_state, schemaVersion, provenance}`.
- *BESS sandbox screening* — `area_capacity_summary.json`: per area `{licence_area, gsp:[{name, import_mw, export_mw, rag}], primary_headroom_mw, ecr_pipeline_mw, method_state}`.
- *spider_maya graph* — nodes `{id, type: operator|portal|dataset, name, provenance_declared}`, edges `data_feed {from: portal, to: dataset, cadence, licence, state}`.
- *Renewables dashboard* — `queue_summary.json`: `{area, tec_mw_by_gate, ecr_accepted_mw, dfes_scenario_headroom, updated_at}`.

**Incremental update strategy.** Classify: static reference (licence_areas, operators, GSP polygons) — refresh rarely; monthly (ECR); semi-annual (LTDS May/Nov); annual (DFES/NSHR); twice-weekly (NESO TEC/registers); live (faults — out of scope). Hive-partition by `dataset_id/dataset_modified` so cron refreshes touch only changed partitions; gate refresh on `dataset_modified`/`last_modified`/SHA-256 change. `workflow_dispatch` first, then cron; SHA-pinned actions; least-privilege tokens; keep heavy truth in Parquet/DuckDB, emit only compact JSON/GeoJSON to renderers.

**Schema-drift defence.** Per-dataset column-mapping config keyed by schemaVersion; validation fails loudly and marks the dataset degraded in the registry rather than silently ingesting wrong columns. This matters concretely because portals rename fields (e.g. NESO phasing out Project IDs in favour of Project Nos in the TEC register; UKPN noting February-2024 ECR fixes causing “fallout”).

## Recommendations

**Phase 2 (deepen fetchers, static + monthly).** Implement the two reusable fetcher classes (ODS `/exports`, CKAN `datastore_search`). Ingest ECR (all DNOs — both tiers), GSP/substation polygons, licence-area boundaries. Wire schema-drift config + SHA-256 audit receipts. Ship `licence_areas.geojson` + `area_capacity_summary.json`. *Threshold to proceed:* all 14 GB areas resolve with ECR joined and SHA receipts reproducible run-to-run.

**Phase 3 (capacity + scenarios).** Add LTDS (tabular now, CIM EQ profiles as published — request access where triaged “Shared”), DFES/NSHR headroom, NESO TEC/Interconnector/Embedded registers. Build spider_maya graph + `queue_summary.json`. *Threshold:* headroom screening panel renders per-area from Parquet/DuckDB with degraded states shown honestly.

**Phase 4 (Ireland + flexibility).** Add flexibility tender data and the all-island degraded sources (ESB heatmap, EirGrid generators, SONI/NIE, interconnector edges). *Threshold:* every Irish source explicitly marked declared/degraded; interconnectors present as graph edges (Moyle/EWIC/Greenlink = 1,500 MW SEM-GB, Celtic pending).

**Change triggers.** LTDS CIM Stage 2/3 (29 May / 30 Nov 2026) — add CIM SC/SYSCAP/GL profiles when live; TMO4+ Gate reform maturing — split TEC by stage/technology once NESO refines the aggregate; if a portal migrates platform (e.g. SSEN Distribution to ODS/CKAN) switch to the reusable class; if the BSI Engagement Hub relocates artefacts again, update the artefact registry rather than hard-coding URLs.

## Caveats

- Opendatasoft per-domain quotas are not universally published; they are delivered via `X-RateLimit-*` headers reset daily at midnight UTC, so treat rate limits as portal-specific and back off on HTTP 429.
- Some UKPN tables require registration; several Irish/NI sources are interactive-map or PDF only — coverage there is screening-grade, not certification-grade, consistent with house doctrine (screening not certification, degraded shown honestly).
- Precise CC-version attributions for ENWL/SSEN come partly from a third-party aggregator (MapYourGrid); confirm on each portal’s dataset licence tab before relying on them. SPEN’s dual licence names and UKPN’s CC BY 4.0 (for triages) are confirmed from the operators’ own portals.
- LTDS reform timings are derogated and may slip further; the CIM artefacts have already moved (ENA GitHub → BSI Engagement Hub), so hard-coded artefact URLs will break.
- ECRs “should be updated monthly” but DNOs warn some projects/updates are missed and cells may be unpopulated; the exact point of connection is not given — use for screening, verify with the DNO before siting decisions.
- Interconnector and SEM market data (SEMO/SEMOpx) may be registration-gated; mark accordingly.
- Greenlink’s rating is quoted as 500 MW by SONI/EPEX and 504 MW nameplate elsewhere; both figures appear in sources and the small discrepancy should be noted rather than silently resolved.