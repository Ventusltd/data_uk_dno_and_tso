from __future__ import annotations

import csv
import json
from pathlib import Path

from lib.hashing import sha256_file
from lib.audit import write_receipts

DECLARED_DIR = Path("data/declared")
BUILD_JSON_DIR = Path("build/json/declared")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(name: str, rows: list[dict[str, str]]) -> Path:
    BUILD_JSON_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_JSON_DIR / f"{name}.json"
    out.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def main() -> int:
    outputs: dict[str, str] = {}
    for csv_path in sorted(DECLARED_DIR.glob("*.csv")):
        rows = read_csv(csv_path)
        out = write_json(csv_path.stem, rows)
        outputs[str(out)] = sha256_file(out)
    write_receipts("build_declared", {"status": "OK", "outputs": outputs})
    print(f"Built {len(outputs)} declared JSON outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
