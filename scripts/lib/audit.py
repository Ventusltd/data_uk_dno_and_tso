from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_receipts(run_name: str, payload: dict[str, Any]) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("audit") / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stamp}.json"
    md_path = out_dir / f"{stamp}.md"
    payload = {"run_name": run_name, "created_at": utc_now(), **payload}
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"# {run_name} audit receipt", "", f"Created: {payload['created_at']}", ""]
    for key, value in payload.items():
        if key == "created_at":
            continue
        lines.append(f"- {key}: `{value}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
