# Data Architecture Blueprint — `Ventusltd/data_uk_dno_and_tso`

## TL;DR

- Build a pure “data repo” twin of `data-gb-electricity`: Hive-partitioned Parquet as heavy truth, DuckDB (+spatial) as the query engine, compact RFC 7946 GeoJSON/JSON as the only thing renderers touch, with `schemaVersion`/`methodState`/`source` and declared-vs-derived provenance stamped on every row.
- Model the operator landscape as five linked entity tables — `operators` (groups), `licence_areas` (14 GB areas + NI + RoI, keyed on the MPAN distributor ID 10–23), `network_stats` (per operator per year), `mpan_distributor` (canonical join key), and `department_lineage` (DECC→BEIS→DESNZ) — and keep operator (NESO/EirGrid/SONI) distinct from owner (NGET/SPT/SSEN‑T) as a first-class distinction.
- Ship in four phases: (1) declared operator entities + licence-area GeoJSON + one stats table + MPAN table; (2) per-DNO OpenDataSoft/CKAN fetchers; (3) NESO FES/ETYS; (4) Ireland (ESB/EirGrid/SONI/NIE) — each phase gated by the same auditor checks (clean clone, deterministic re-run, provenance legal, hashes match).

## Key Findings

**The landscape is cleanly modellable and almost entirely open.** Great Britain has 14 licensed DNO areas run by six groups, keyed 1:1 to MPAN distributor IDs 10–23. NESO — the National Energy System Operator — began operating on 1 October 2024, after the UK government acquired the electricity system operator (ESO) division from National Grid plc for £630 million. NESO operates but owns no transmission; the transmission licence it inherited is an *operator* (ESO) licence, distinct from the transmission *owners*: NGET (England & Wales), SP Transmission and SSEN Transmission (Scotland), per the DESNZ/Ofgem Decision Notice of 13 September 2024 effective 1 October 2024. The island of Ireland adds NIE Networks (NI distribution/transmission owner, regulated by the NI Utility Regulator not Ofgem) and ESB Networks (RoI DSO), with EirGrid (RoI TSO) and SONI (NI TSO) as system operators. This maps to an operator-vs-owner distinction that must be explicit in the schema.

**Authoritative open boundary data exists and is directly fetchable.** NESO’s Data Portal publishes “GIS Boundaries for GB DNO Licence Areas” as GeoJSON and ESRI shapefile (versions 20200506 and 20240503) via a CKAN API, under the NESO Open Licence (OGL-v3-compatible, attribution “Supported by National Energy SO Open Data”).  Note the GeoJSON is delivered in EPSG:27700 (British National Grid) and boundaries are explicitly “approximate.”

**Every DNO runs an open data portal, mostly on OpenDataSoft (“Huwise”).** UKPN, SP Energy Networks, Electricity North West, Northern Powergrid and NIE Networks all use OpenDataSoft (queryable via the Explore API v2.1 / ODSQL); NGED uses a CKAN portal (`connecteddata.nationalgrid.co.uk/api/3/action/…`, API token required from 1 June 2024);  SSEN uses `data.ssen.co.uk`. UKPN publishes a “Network Statistics” dataset (`ukpn-network-statistics`) compiled from its annual Ofgem RIGs submissions — the model for the `network_stats` table.

**The government layer needs a rename-proof design.** DECC (2008–2016) → BEIS (2016–2023) → DESNZ (2023–present); DESNZ was established on 7 February 2023 in a cabinet reshuffle under Rishi Sunak, taking the energy-policy responsibilities of the former BEIS. Because department names change every political cycle, use a stable folder `uk_government_public_data/` and track the naming as data in a `department_lineage` table; preserve the publishing-department name at time of publication as row metadata.

## Details

### 1. The operator landscape and how to model it

**Canonical entity model (five tables).** Keep three concepts strictly separate: **group** (the brand/corporate parent), **licensed entity** (the plc that holds the Ofgem licence), and **role** (distribution owner-operator, transmission owner, or system operator). The requester’s note “WPD (NGET?)” resolves as: **NGED** = National Grid Electricity Distribution, the distribution business formerly Western Power Distribution (licence areas 11/14/21/22); **NGET** = National Grid Electricity Transmission, the transmission *owner* in England & Wales. These are different licensed entities and must be modelled as distinct rows — NGED is a DNO group, NGET is a transmission owner (TO).

`operators` table (entity/group table, declared):

|column                                        |type        |notes                                                                                                                                       |
|----------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------|
|operator_id                                   |VARCHAR (PK)|slug, e.g. `ukpn`, `nged`, `spen`, `ssen`, `npg`, `enwl`, `nie_networks`, `esb_networks`, `neso`, `nget`, `spt`, `ssen_t`, `eirgrid`, `soni`|
|legal_name                                    |VARCHAR     |e.g. “UK Power Networks Holdings Limited”                                                                                                   |
|brand_name                                    |VARCHAR     |e.g. “UK Power Networks”                                                                                                                    |
|role                                          |VARCHAR     |enum: `DNO`, `IDNO`, `TO` (transmission owner), `SO` (system operator), `DSO`                                                               |
|jurisdiction                                  |VARCHAR     |`GB`, `NI`, `RoI`                                                                                                                           |
|regulator_id                                  |VARCHAR     |FK → regulator (`ofgem`, `niur`, `cru`)                                                                                                     |
|parent_company                                |VARCHAR     |e.g. “Iberdrola”, “Berkshire Hathaway Energy”, “ESB Group”                                                                                  |
|is_owner                                      |BOOLEAN     |owns physical assets                                                                                                                        |
|is_system_operator                            |BOOLEAN     |operates but may not own                                                                                                                    |
|schemaVersion, methodState, source, provenance|            |stamped on every row                                                                                                                        |

Model NESO as `role='SO'`, `is_owner=false`, `is_system_operator=true`. Model NGET/SPT/SSEN‑T as `role='TO'`, `is_owner=true`, `is_system_operator=false`. This directly answers “is NESO TSO relevant”: it is the operator, not the owner — capture the operates-vs-owns relationship in a `transmission_ownership` bridge table (`region → owner_operator_id → system_operator_id`).

**IDNOs as a first-class distinction.** DNOs hold a geographic licence; IDNOs (role=`IDNO`) hold non-geographic licences and can operate anywhere in GB, with MPAN distributor IDs 24+. The licensed IDNO population includes GTC (operating The Electricity Network Company Ltd and Independent Power Networks Ltd),  ESP Electricity, Vattenfall Networks Ltd, Last Mile, Harlaxton Energy Networks, Eclipse Power Networks, Energy Assets, Fulcrum, Indigo Power, Leep Utilities, MUA, and others. Keep IDNOs in the same `operators` schema with `role='IDNO'` so a future `data-idnos` repo extends by simply adding rows — no schema change.

**MPAN distributor ID is the canonical join key.** The `mpan_distributor` table (declared, from dcmf.co.uk cross-checked against Elexon and supplier lookup PDFs):

|MPAN ID|GSP Group|Licence area                     |Licensed DNO entity                                       |Group (operator_id)|
|-------|---------|---------------------------------|----------------------------------------------------------|-------------------|
|10     |_A       |Eastern England                  |Eastern Power Networks plc                                |ukpn               |
|11     |_B       |East Midlands                    |National Grid Electricity Distribution (East Midlands) plc|nged               |
|12     |_C       |London                           |London Power Networks plc                                 |ukpn               |
|13     |_D       |Merseyside & North Wales (Manweb)|SP Manweb plc                                             |spen               |
|14     |_E       |West Midlands                    |National Grid Electricity Distribution (West Midlands) plc|nged               |
|15     |_F       |North Eastern                    |Northern Powergrid (Northeast) plc                        |npg                |
|16     |_G       |North Western                    |Electricity North West Ltd                                |enwl               |
|17     |_P       |North Scotland                   |Scottish Hydro Electric Power Distribution plc (SHEPD)    |ssen               |
|18     |_N       |South Scotland                   |SP Distribution plc                                       |spen               |
|19     |_J       |South Eastern                    |South Eastern Power Networks plc                          |ukpn               |
|20     |_H       |Southern England                 |Southern Electric Power Distribution plc (SEPD)           |ssen               |
|21     |_K       |South Wales                      |National Grid Electricity Distribution (South Wales) plc  |nged               |
|22     |_L       |South Western England            |National Grid Electricity Distribution (South West) plc   |nged               |
|23     |_M       |Yorkshire                        |Northern Powergrid (Yorkshire) plc                        |npg                |

Note the GSP Group letter is **not** sequential with the MPAN ID (17=_P, 18=_N, 20=_H) — store the letter explicitly, never derive it. For RIIO-ED2 reporting, note Ofgem keeps ENWL and SPEN as separate DNO groups even after Iberdrola’s October 2024 acquisition of ENWL (trading as “SP Electricity North West”) — the licensed entity remains Electricity North West Ltd, so model the trading-name change as an attribute with an effective date, not a new entity.

### 2. Licence area geography

**`licence_areas` table (declared):** one row per area (14 GB + NIE Networks + ESB Networks). Columns: `licence_area_id` (e.g. `_A`), `mpan_id` (10–23), `area_name`, `operator_id` (FK), `jurisdiction`, plus a pointer to the GeoJSON feature. Store boundaries as **RFC 7946 GeoJSON** (WGS84 / EPSG:4326, `[longitude, latitude]` axis order, right-hand-rule winding) in `data/licence_areas/geojson/`, and the flat attributes as Parquet in `data/licence_areas/parquet/`. Because NESO ships EPSG:27700, the fetcher must reproject to EPSG:4326 for RFC 7946 compliance (DuckDB spatial `ST_Transform`, or store the raw 27700 as `_source` and emit a derived 4326 file).

**Per-operator network stats that are publicly citable:** customer/connection counts, network length (overhead vs underground by voltage), substation counts, peak demand, RIIO-ED2 allowances, connections/ECR data, DFES forecasts, and flexibility tender volumes. The authoritative cross-comparable source is **Ofgem RIIO-ED2 regulatory data / each DNO’s RIGs submissions**; the DNOs republish RIGs-derived stats on their own portals (UKPN’s `ukpn-network-statistics` being the cleanest example). Current headline figures for the `network_stats` seed (declared, each attributed to its operator):

- **UK Power Networks** — its own site states “approximately eight million customers” across an area of “30,000 square kilometres” via three licensed networks; an older CKI/HK Electric fact sheet gives 47,391 km overhead + 134,767 km underground and 29,165 km². (Store the exact figure and its source per row; see caveat on the pending ENGIE acquisition materials citing 8.5 million.)
- **National Grid Electricity Distribution** — around 8 million connections, over 230,000 km of network, around 55,500 km² (largest by geography), per NGED’s FY2024/25 Annual Report.
- **SP Energy Networks** — around 3.5 million connections (about 2.0m SPD + 1.5m Manweb), over 100,000 km of cable and line. 
- **SSEN** — around 3.9 million connections across SHEPD (North Scotland) and SEPD (Southern England); verify against SSEN RIIO-ED2 submissions as SSEN does not prominently publish a single consolidated figure.
- **Northern Powergrid** — around 3.9 million customers, roughly 98,000 km of network, around 25,000 km², 63,000+ substations.  
- **Electricity North West** — around 2.4 million properties, roughly 59,000 km of network (about 12,000 km overhead, 47,000 km underground), 38,000 transformers. 
- **NIE Networks** — the nienetworks.co.uk homepage states NIE Networks “owns the electricity transmission and distribution network and operates the electricity distribution network which transports electricity to over 966,000 customers”; network is roughly 2,200 km transmission + ~47,000 km distribution.
- **ESB Networks** — reports “more than 2.5 million customers” and a network of “over 160,000 km of overhead lines, 28,000 km of underground cables and more than 800 high-voltage substations” (ESB Networks “Innovation 2026” consultation, esbnetworks.ie); connected 37,558 new customers in 2024.

Treat all of these as `declared` with a `source` string and `retrieved_at`; anything computed (e.g. underground percentage) is `derived`.

### 3. Government and regulator layer

**Stable folder that survives renaming:** `data/government/uk_government_public_data/`. Inside, partition by `dataset=` then `vintage=` (never by department). Track department identity as data in `department_lineage`:

|dept_id|short_name|full_name                                             |valid_from|valid_to  |
|-------|----------|------------------------------------------------------|----------|----------|
|decc   |DECC      |Department of Energy and Climate Change               |2008-10-03|2016-07-14|
|beis   |BEIS      |Department for Business, Energy & Industrial Strategy |2016-07-14|2023-02-07|
|desnz  |DESNZ     |Department for Energy Security and Net Zero           |2023-02-07|(open)    |

DESNZ’s `valid_from` of 2023-02-07 is confirmed: it “was established on 7 February 2023 by a cabinet reshuffle under the Rishi Sunak premiership [and] took on the energy policy responsibilities of the former [BEIS].” Each government dataset row carries `published_by_dept_id` (the name *at time of publication*) so a 2015 REPD vintage stays stamped “DECC” forever while the path stays stable. Datasets to cover: **DUKES** (Digest of UK Energy Statistics), **Energy Trends**, **sub-national electricity consumption statistics**, **REPD** (Renewable Energy Planning Database — quarterly, managed by Barbour ABI for DESNZ; captures every project >150kW with capacity, technology, planning status, grid coordinates), and heat-pump/EV statistics.

**Regulator layer** in `data/regulator/ofgem/` (plus `niur/` and `cru/` for Ireland): RIIO price controls (RIIO-ED2 covers 2023–2028), and the **Ofgem licence register** — the authoritative list of all licensed DNOs, IDNOs and suppliers. Ofgem’s RIIO-ED2 annual reports and RIGs reporting packs are the definitive source for the DNO-group/14-DNO appendix and for cross-comparable stats.

### 4. Repo architecture

Following the `data-gb-electricity` pattern (partitioned Parquet + DuckDB, deterministic fetchers, exactly-scoped workflows, audit receipts), extended:

```
data_uk_dno_and_tso/
  config/
    sources.json                 # declared source registry (see below)
  data/
    operators/                   # entity tables (small, unpartitioned Parquet)
      operators.parquet
      mpan_distributor.parquet
      transmission_ownership.parquet
    licence_areas/
      geojson/ area=<id>.geojson  # RFC 7946, EPSG:4326, compact
      parquet/ licence_areas.parquet
    network_stats/               # Hive-partitioned
      operator=<id>/year=<yyyy>/data.parquet
    government/
      uk_government_public_data/
        dataset=<name>/vintage=<yyyyqn>/data.parquet
    regulator/
      ofgem/ dataset=<name>/vintage=<>/data.parquet
      niur/  ...
      cru/   ...
  scripts/                       # one deterministic fetcher per source
    fetch_neso_dno_boundaries.py
    fetch_ukpn_network_stats.py
    fetch_nged_connected_data.py
    fetch_repd.py
    fetch_fes_building_blocks.py
    fetch_esb_eirgrid.py
    lib/ (provenance.py, hashing.py, audit.py, http.py)
  audit/
    <script>/<run_ts>.md
    <script>/<run_ts>.json
  docs/
    DATA_SOURCES.md
    DEFINITIONS.md
    CHANGELOG.md
    ARCHITECTURE.md   # this blueprint
  .github/workflows/
    fetch.yml         # workflow_dispatch first, cron once idempotent
    audit.yml         # verifies hashes + provenance legality
```

**Partitioning best practice for this shape.** Three distinct shapes call for three treatments: (a) **small entity tables** (`operators`, `mpan_distributor`, ~14–60 rows) — a single unpartitioned Parquet each; partitioning tiny tables creates needless small files, which DuckDB’s own guidance warns is expensive (“Writing data into many small partitions is expensive”). (b) **Yearly stats** (`network_stats`) — Hive-partition by `operator=/year=`, one file per partition, so a query for one operator-year reads one file via partition pushdown (DuckDB automatically pushes filters on partition keys down into the file scan). (c) **Geospatial** — keep GeoJSON as files (renderer-ready) and mirror attributes into Parquet; do not stuff large geometries into the yearly Parquet. Target reasonably sized row groups and avoid thousands of tiny partitions.

**DuckDB query patterns.**

```sql
INSTALL spatial; LOAD spatial;
-- Read licence-area boundaries straight from GeoJSON (ST_Read replacement scan)
CREATE TABLE areas AS SELECT * FROM ST_Read('data/licence_areas/geojson/*.geojson');
-- Partition-pruned stats read
SELECT * FROM read_parquet('data/network_stats/*/*/data.parquet', hive_partitioning=true)
WHERE operator='ukpn' AND year=2025;
-- Join stats to geometry via MPAN key, emit compact GeoJSON for the atlas
COPY (
  SELECT a.geom, a.area_name, s.customers, s.network_km
  FROM areas a
  JOIN read_parquet('data/network_stats/*/*/data.parquet', hive_partitioning=true) s
    ON a.mpan_id = s.mpan_id
  WHERE s.year = 2025
) TO 'build/atlas_dno_overlay.geojson'
WITH (FORMAT GDAL, DRIVER 'GeoJSON', SRS 'EPSG:4326', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES');
```

Renderers (atlas v8, SLD sandbox, spiders) consume only the compact derived GeoJSON/JSON emitted by these `COPY` steps — never the Parquet or DuckDB directly.

**Deterministic fetcher pseudocode (PVLive style):**

```python
def fetch(source_id):
    cfg = load_sources_json()[source_id]
    working_url = None
    for url in cfg["candidate_urls"]:      # try candidate shapes until one resolves
        r = http_get(url)
        if r.ok:
            working_url = url; break
    if not working_url:
        emit_audit(source_id, status="FAIL", failures=cfg["candidate_urls"]); raise
    rows = parse(r, cfg["format"])
    for row in rows:                        # stamp provenance on every row
        row["schemaVersion"] = cfg["schemaVersion"]
        row["methodState"]   = cfg["methodState"]     # e.g. "screening"
        row["source"]        = cfg["attribution"]
        row["provenance"]    = "declared"             # or "derived" for computed rows
        row["retrieved_at"]  = now_iso()
    out = write_parquet_or_geojson(rows, cfg["target"])
    sha = sha256_file(out)                  # SHA-256 over outputs
    emit_audit(source_id, status="OK", rows=len(rows), working_url=working_url,
               bytes=filesize(out), sha256=sha)   # markdown + JSON receipt
```

**`config/sources.json` (declared source registry)** — one object per source with `candidate_urls`, `api_pattern`, `format`, `licence`, `attribution`, `schemaVersion`, `methodState`, `target`. Example entries:

- `neso_dno_boundaries`: CKAN, `https://api.neso.energy/api/3/action/datapackage_show?id=gis-boundaries-for-gb-dno-license-areas`; resource `gb-dno-license-areas-20240503-as-geojson.geojson`; licence “NESO Open Licence”.
- `ukpn_network_stats`: OpenDataSoft, `https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-network-statistics/exports/parquet`.
- `nged_connected_data`: CKAN, `https://connecteddata.nationalgrid.co.uk/api/3/action/…` (token in a repo secret; header `Authorization`).
- `repd`: GOV.UK “Renewable Energy Planning Database: quarterly extract ” (OGL v3).
- `fes_building_blocks`: `https://api.neso.energy/dataset/30df2649-…/resource/…/download/fes2025_bb1_v006.csv`.

### 5. What feeds what

|This repo produces                   |Feeds                                                                   |How                                                                                           |
|-------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
|`licence_areas` GeoJSON + `operators`|**repd_grid_atlasv8** overlay layer; **spider** graph nodes             |compact GeoJSON overlay; spider_maya catalogues repo as a declared node with `data_feed` edges|
|`network_stats` (per operator/year)  |**uk_energy_tracking_v6** + **gis-sld-financial-sandbox** context panels|compact JSON per operator                                                                     |
|`mpan_distributor`                   |future **behind-the-meter** and **IDNO** repos                          |canonical join key (MPAN 10–23, IDNOs 24+)                                                    |
|NESO **FES/ETYS** building blocks    |**uk_renewables_pipeline** analytics; **BESS sandbox V8**               |derived scenario JSON                                                                         |
|Government **REPD**                  |already feeds atlas (2819 projects / 52.3 GW pipeline)                  |join REPD grid coordinates → licence area via spatial join                                    |

spider_maya ingests the repo by reading `config/sources.json` and the `docs/` files; the repo becomes a declared node whose outgoing `data_feed` edges point at each consuming app URL, and whose incoming edges are the external APIs in the registry.

### 6. Licensing and attribution

Record licence **per dataset** in `sources.json` and store the attribution string with the data (as the `source` column), so redistribution as Parquet stays compliant.

|Source                                                     |Licence                                                     |Attribution string to store                                                         |
|-----------------------------------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------|
|NESO Data Portal (boundaries, FES, ETYS)                   |NESO Open Licence (OGL-v3-compatible)                       |“Supported by National Energy SO Open Data”                                         |
|DESNZ statistics (DUKES, Energy Trends, sub-national, REPD)|OGL v3                                                      |“Contains public sector information licensed under the Open Government Licence v3.0”|
|Ofgem (licence register, RIIO-ED2)                         |OGL v3                                                      |as above                                                                            |
|DNO OpenDataSoft portals (UKPN, SPEN, ENWL, NPg, NIE)      |per-dataset (commonly OGL v3 / CC-BY / bespoke portal terms)|check each dataset’s stated licence; store verbatim                                 |
|NGED Connected Data Portal                                 |per-dataset; token required                                 |store per-dataset licence                                                           |
|EirGrid / SONI / SEMO                                      |EirGrid data terms (check per dataset)                      |“Data © EirGrid/SONI”                                                               |
|ESB Networks                                               |ESB Networks terms (check per dataset)                      |“Data © ESB Networks”                                                               |

OGL v3 is explicitly compatible with CC-BY 4.0 and the Open Data Commons Attribution Licence, so mixed OGL/CC-BY redistribution is safe; the only obligation is attribution, which the `source` column satisfies. Ireland’s EirGrid/SONI and ESB terms are **not** blanket-open — record each dataset’s licence explicitly and default to `methodState="restricted"` until the licence is confirmed.

### 7. Phased build plan with acceptance checks

Every phase must pass the `data-gb-electricity` auditor gate: **(a)** clean clone builds with no manual steps; **(b)** deterministic re-run produces byte-identical outputs (SHA-256 match); **(c)** provenance legal — every row has `schemaVersion`/`methodState`/`source`/`provenance` and every source has a recorded licence; **(d)** hashes recorded in audit receipts match on re-run.

- **Phase 1 — Simple version (declared only).** `operators` + `licence_areas` boundaries (NESO GeoJSON, reprojected to 4326) + one `network_stats` table (customers, area, network length) + the `mpan_distributor` table. Acceptance: 14 areas + NI + RoI present; every row stamped; NESO attribution stored; boundary GeoJSON validates as RFC 7946; hashes stable.
- **Phase 2 — Per-operator portal fetchers.** OpenDataSoft fetchers (UKPN, SPEN, ENWL, NPg, NIE) via Explore API v2.1; NGED CKAN fetcher with token; SSEN. Richer stats (OH/UG by voltage, substations, peak demand, ECR/connections). Acceptance: each fetcher tries candidate URLs, emits audit receipt, degrades honestly (never fake-green) when a portal is down.
- **Phase 3 — NESO FES/ETYS.** FES building-block CSVs + ETYS regional data → derived scenario Parquet feeding pipeline analytics and BESS sandbox. Acceptance: FES vintage stamped; GB→regional disaggregation flagged `derived`.
- **Phase 4 — Ireland deep data.** ESB Networks, EirGrid, SONI, NIE Networks. Acceptance: each Irish dataset’s licence explicitly recorded; anything without confirmed open terms marked `methodState="restricted"` and excluded from redistributed Parquet until cleared.

## Recommendations

1. **Start Phase 1 this week with only declared data.** Seed `operators`, `mpan_distributor` (the 14-row table above), `licence_areas` from NESO’s `gb-dno-license-areas-20240503` GeoJSON, and a hand-entered `network_stats` seed from the headline figures above. This alone unblocks the atlas overlay and spider nodes. **Threshold to proceed to Phase 2:** clean-clone deterministic re-run yields identical SHA-256 and the boundary GeoJSON passes an RFC 7946 validator.
1. **Write the fetcher library (`lib/`) once, reuse everywhere.** The PVLive-style try-candidate-URLs + stamp + hash + audit loop should live in `lib/` so every `scripts/fetch_*.py` is ~30 lines of config. **Threshold:** two fetchers (NESO boundaries + UKPN stats) share the same lib with zero copy-paste before writing the rest.
1. **Keep `workflow_dispatch`-only until idempotent.** Do not add cron until a manual re-run demonstrably produces byte-identical outputs. SHA-pin all actions, least-privilege `GITHUB_TOKEN`, and restrict writes to `data/` and `audit/`. **Threshold to enable cron:** three consecutive manual runs hash-identical.
1. **Treat Ireland as licence-gated.** Build the fetchers in Phase 4 but hold redistribution of any ESB/EirGrid/SONI dataset whose terms are not confirmed open; mark `methodState="restricted"`. **Threshold:** a written licence confirmation per dataset before it enters redistributed Parquet.
1. **Make `department_lineage` and the operator-vs-owner split load-bearing from day one.** They are cheap now and prevent painful path/identity migrations later when DESNZ is renamed or transmission ownership changes.

## Caveats

- NESO DNO licence-area boundaries are officially “approximate,” originally shared by WPD/NGED, “probably a little outdated and not 100% accurate,” and delivered in EPSG:27700 — reproject and label them screening-grade, never authoritative cadastre.
- Some DNO OpenDataSoft datasets require free registration/login to download; the Explore API export endpoints generally work unauthenticated but rate-limit — build backoff into the fetcher lib.
- Per-operator headline stats vary by source and date (e.g. UKPN’s own “approximately eight million”/30,000 km² vs the ~8.5 million cited in the pending ENGIE acquisition materials; ESB 2.3–2.5m and 150k/23k vs 160k/28k km across documents; NIE 900k–966k+). Store the exact `source` and `retrieved_at` per row and prefer Ofgem RIIO-ED2/RIGs for cross-comparable figures; the seed numbers above are indicative and must be re-verified per operator before publication.
- The pending Iberdrola/ENWL and ENGIE/UKPN ownership changes are corporate events in flux — model ownership with effective dates rather than hard-coding a parent.
- NGED’s Connected Data Portal requires an API token (since 1 June 2024) and is CKAN, not OpenDataSoft — its fetcher differs from the DNO OpenDataSoft pattern.
- IDNO MPAN IDs (24+) and the full IDNO population are more volatile than the 14 DNOs; treat the IDNO list as a living table sourced from Ofgem’s licence register.
- DuckDB’s spatial `GEOMETRY` type does not currently store SRID/CRS metadata, so track the CRS yourself in the pipeline (source 27700 → derived 4326) and set `SRS 'EPSG:4326'` explicitly on every GeoJSON `COPY` export.
