# Definitions

## DNO

Distribution Network Operator. A licensed geographic electricity distribution network operator in Great Britain.

## IDNO

Independent Distribution Network Operator. A licensed non-geographic distribution network operator. IDNOs can operate networks inside another DNO's geographic area.

## TSO / SO

System operator. In this repo, the system operator role is separated from transmission ownership.

## TO

Transmission owner. The asset-owning transmission licence holder for a transmission region.

## NESO

National Energy System Operator. Modelled as a system operator, not an owner of transmission assets.

## MPAN distributor ID

Canonical GB electricity distribution-area join key. The DNO area IDs 10 to 23 map to the 14 GB licensed distribution areas.

## Licence area

A regulated geographic electricity distribution area. For GB this means the 14 DNO areas. For this repo the model is extended to Northern Ireland and the Republic of Ireland for practical atlas coverage.

## Government public data

A stable folder and data concept used to avoid department-name churn. Department names such as DECC, BEIS and DESNZ are treated as data lineage, not as permanent folder names.

## Declared data

Human-maintained seed data entered with source notes and provenance fields.

## Fetched data

Data downloaded by deterministic scripts from a declared source registry.

## Derived data

Data computed from declared or fetched sources. Derived rows must never hide their source lineage.

## Restricted data

Data whose licence has not been cleared for redistribution. It may be referenced in source registries but must not be redistributed as open Parquet until cleared.
