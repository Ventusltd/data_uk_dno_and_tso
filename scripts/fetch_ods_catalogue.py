from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from lib.audit import write_receipts
from lib.hashing import sha256_file
from lib.opendatasoft import ODSPortal, list_datasets


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "config" / "sources.json"


def load_sources() -> list[dict]:
    return json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]


def portal_base_from_catalogue_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch OpenDataSoft catalogue metadata for one configured source.")
    parser.add_argument("source_id")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    sources = {s["source_id"]: s for s in load_sources()}
    source = sources.get(args.source_id)
    if not source:
        raise SystemExit(f"Unknown source_id: {args.source_id}")
    if source.get("portal_family") != "opendatasoft":
        raise SystemExit(f"Source is not opendatasoft: {args.source_id}")
    if not source.get("candidate_urls"):
        raise SystemExit(f"No candidate URLs for source: {args.source_id}")

    working_url = source["candidate_urls"][0]
    portal = ODSPortal(
        base_url=portal_base_from_catalogue_url(working_url),
        api_key_env=source.get("api_key_env"),
    )
    payload = list_datasets(portal, limit=args.limit)

    out_dir = ROOT / source.get("target", f"audit/source_catalogues/{args.source_id}/")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "catalogue.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_receipts(
        "fetch_ods_catalogue",
        {
            "status": "OK",
            "source_id": args.source_id,
            "working_url": working_url,
            "output": str(out_path),
            "sha256": sha256_file(out_path),
            "dataset_count_hint": len(payload.get("results", [])) if isinstance(payload, dict) else None,
        },
    )
    print(f"Fetched ODS catalogue for {args.source_id}: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
