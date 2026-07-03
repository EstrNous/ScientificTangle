from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_rg(pattern: str, path: str, glob: str | None = None) -> list[str]:
    cmd = ["rg", pattern, path]
    if glob:
        cmd.extend(["--glob", glob])
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr or result.stdout)
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_no_app_imports() -> list[str]:
    matches = run_rg(r"from app\.", "services", glob="*/app/**/*.py")
    return [f"P0-01: from app.* in runtime: {line}" for line in matches]


def check_no_up_auth() -> list[str]:
    matches = run_rg("up-auth", "Makefile")
    return [f"P0-10: up-auth remnant: {line}" for line in matches]


def check_no_init_sql_mount() -> list[str]:
    matches = run_rg(r"init\.sql", "docker-compose.yml")
    path = ROOT / "infra" / "postgres" / "init.sql"
    issues = [f"P0-03: init.sql file still exists: {path}"] if path.exists() else []
    issues.extend(f"P0-03: init.sql mount: {line}" for line in matches)
    return issues


def check_no_page_mock_imports() -> list[str]:
    matches = run_rg(r"from ['\"].*api/mock/", "ui/src/pages")
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
