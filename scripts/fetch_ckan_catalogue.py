from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from lib.audit import write_receipts
from lib.ckan import CKANPortal, get_action
from lib.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "config" / "sources.json"


def load_sources() -> list[dict]:
    return json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]


def portal_base_from_action_url(url: str) -> str:
    parsed = urlparse(url)
    marker = "/api/3/action"
    base_path = parsed.path.split(marker)[0] if marker in parsed.path else ""
    return f"{parsed.scheme}://{parsed.netloc}{base_path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch CKAN package_list catalogue metadata for one configured source.")
    parser.add_argument("source_id")
    args = parser.parse_args()

    sources = {s["source_id"]: s for s in load_sources()}
    source = sources.get(args.source_id)
    if not source:
        raise SystemExit(f"Unknown source_id: {args.source_id}")
    if source.get("portal_family") != "ckan":
        raise SystemExit(f"Source is not ckan: {args.source_id}")
    if not source.get("candidate_urls"):
        raise SystemExit(f"No candidate URLs for source: {args.source_id}")

    working_url = source["candidate_urls"][0]
    portal = CKANPortal(
        base_url=portal_base_from_action_url(working_url),
        api_key_env=None,
        min_delay_seconds=float(source.get("min_delay_seconds", 1.0)),
    )
    payload = get_action(portal, "package_list")

    out_dir = ROOT / source.get("target", f"audit/source_catalogues/{args.source_id}/")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "catalogue.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = payload.get("result", []) if isinstance(payload, dict) else []
    write_receipts(
        "fetch_ckan_catalogue",
        {
            "status": "OK" if payload.get("success") else "DEGRADED",
            "source_id": args.source_id,
            "working_url": working_url,
            "output": str(out_path),
            "sha256": sha256_file(out_path),
            "package_count_hint": len(result) if isinstance(result, list) else None,
        },
    )
    print(f"Fetched CKAN catalogue for {args.source_id}: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
