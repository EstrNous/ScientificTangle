from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
DICTIONARIES = ROOT / "dictionaries"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping at root")
    return data


def validate_ontology_files() -> list[str]:
    errors: list[str] = []
    for path in sorted(ONTOLOGY.glob("*.yaml")):
        if path.name == "core_schema.yaml":
            continue
        try:
            load_yaml(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def validate_dictionaries() -> list[str]:
    errors: list[str] = []
    if not DICTIONARIES.exists():
        return errors
    for path in sorted(DICTIONARIES.rglob("*.yaml")):
        try:
            load_yaml(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def main() -> int:
    errors = validate_ontology_files() + validate_dictionaries()
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print("ontology and dictionaries: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
