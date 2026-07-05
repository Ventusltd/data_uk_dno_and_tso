from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def required_columns(schema_path: Path) -> set[str]:
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    return set(data.get("required", []))


def header_columns(csv_path: Path) -> set[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        return set(next(reader, []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CSV header against a JSON schema required list.")
    parser.add_argument("schema")
    parser.add_argument("csv_file")
    args = parser.parse_args()

    required = required_columns(ROOT / args.schema)
    columns = header_columns(ROOT / args.csv_file)
    missing = sorted(required - columns)
    if missing:
        print("Schema validation failed")
        for col in missing:
            print(f"- {col}")
        return 1
    print("Schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
