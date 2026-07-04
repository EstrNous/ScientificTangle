from __future__ import annotations

import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def iter_scan_paths(base: Path, glob_pattern: str | None = None) -> list[Path]:
    if not base.exists():
        return []
    if base.is_file():
        return [base]
    paths: list[Path] = []
    for candidate in base.rglob("*"):
        if not candidate.is_file():
            continue
        if glob_pattern:
            rel = candidate.relative_to(base).as_posix()
            if not fnmatch(rel, glob_pattern):
                continue
        paths.append(candidate)
    return paths


def run_search(pattern: str, path: str, glob: str | None = None) -> list[str]:
    regex = re.compile(pattern)
    base = ROOT / path
    matches: list[str] = []
    for file_path in iter_scan_paths(base, glob):
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        rel = file_path.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(lines, start=1):
            if regex.search(line):
                matches.append(f"{rel}:{line_no}:{line}")
    return matches


def check_no_app_imports() -> list[str]:
    matches = run_search(r"from app\.", "services", glob="*/app/**/*.py")
    return [f"P0-01: from app.* in runtime: {line}" for line in matches]


def check_no_up_auth() -> list[str]:
    matches = run_search("up-auth", "Makefile")
    return [f"P0-10: up-auth remnant: {line}" for line in matches]


def check_no_init_sql_mount() -> list[str]:
    matches = run_search(r"init\.sql", "docker-compose.yml")
    path = ROOT / "infra" / "postgres" / "init.sql"
    issues = [f"P0-03: init.sql file still exists: {path}"] if path.exists() else []
    issues.extend(f"P0-03: init.sql mount: {line}" for line in matches)
    return issues


def check_no_page_mock_imports() -> list[str]:
    matches = run_search(r"from ['\"].*api/mock/", "ui/src/pages")
    return [f"P0-13: page imports mock directly: {line}" for line in matches]


def check_makefile_todos() -> list[str]:
    makefile = ROOT / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    if 'echo "TODO:' in text:
        return ["P0-11: Makefile still contains TODO stubs"]
    return []


def main() -> int:
    errors: list[str] = []
    errors.extend(check_no_app_imports())
    errors.extend(check_no_up_auth())
    errors.extend(check_no_init_sql_mount())
    errors.extend(check_no_page_mock_imports())
    errors.extend(check_makefile_todos())

    validate = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_ontology.py")],
        cwd=ROOT,
        check=False,
    )
    if validate.returncode != 0:
        errors.append("ontology/dictionaries validation failed")

    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1

    print("audit_repo: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
