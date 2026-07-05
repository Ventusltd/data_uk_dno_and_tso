# Portal engineering

## Purpose

This document converts the verified useful parts of the Gemini report into practical fetcher design.

## Portal families

| family | use for | implementation state |
|---|---|---|
| OpenDataSoft Explore API v2.1 | UKPN, SPEN, Electricity North West, Northern Powergrid style portals | library scaffold added |
| CKAN Action API | NGED Connected Data and NESO-style catalogues | library scaffold added |
| Metadata/RDF/JSON-LD portal | SSEN Distribution Data Portal | separate future fetcher required |
| Plain file / static downloads | Ireland, PDFs, Excel, ZIPs and legacy files | future hash-gated fetchers required |

## OpenDataSoft rules

Use OpenDataSoft as a bulk-export source, not as an unbounded paginated records source.

Fetcher behaviour:

- discover datasets through `/api/explore/v2.1/catalog/datasets`
- use `/api/explore/v2.1/catalog/datasets/{dataset_id}/records` only for bounded preview and schema checks
- use `/api/explore/v2.1/catalog/datasets/{dataset_id}/exports/{format}` for bulk pulls
- capture response headers where available
- record the working URL in the audit receipt
- do not silently continue if schema drift is detected

## CKAN rules

Fetcher behaviour:

- use `package_list`, `package_show`, `resource_show` and related action endpoints
- support token authentication from environment variables
- rate-limit requests by default
- write a degraded audit state rather than pretending success

## SSEN correction

SSEN Distribution must not be grouped as OpenDataSoft. Treat it as a separate portal stack and do not confuse it with SSEN Transmission.

## Ireland rule

Ireland and Northern Ireland sources default to restricted until licence terms are explicitly cleared.

## Downstream rule

Applications should consume derived JSON or GeoJSON only. They should not depend on live API calls, source PDFs, raw Excel files or direct DuckDB queries.
