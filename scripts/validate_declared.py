from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_PROVENANCE = {"schemaVersion", "methodState", "source", "provenance"}
DECLARED_DIR = Path("data/declared")


def validate_csv(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_PROVENANCE - fields
        if missing:
            errors.append(f"{path}: missing columns {sorted(missing)}")
        for idx, row in enumerate(reader, start=2):
            for col in REQUIRED_PROVENANCE:
                if not (row.get(col) or "").strip():
                    errors.append(f"{path}:{idx}: empty {col}")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in sorted(DECLARED_DIR.glob("*.csv")):
        errors.extend(validate_csv(path))
    if errors:
        print("Declared data validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1
    print("Declared data validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
