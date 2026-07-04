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


def check_base_compose_no_host_ports() -> list[str]:
    compose = ROOT / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    if "ports:" in text:
        return ["prod_perimeter: docker-compose.yml must not publish host ports"]
    return []


def check_prod_compose_nginx_only_ports() -> list[str]:
    compose = ROOT / "docker-compose.prod.yml"
    text = compose.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[str] = []
    current_service: str | None = None
    in_ports = False
    for line in lines:
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-") and line.startswith("  ") and not line.startswith("    "):
            current_service = stripped[:-1]
            in_ports = False
            continue
        if current_service and stripped == "ports:":
            in_ports = True
            continue
        if in_ports and stripped.startswith("- "):
            if current_service != "nginx":
                issues.append(
                    f"prod_perimeter: docker-compose.prod.yml publishes ports for {current_service}"
                )
            in_ports = False
    if "nginx:" not in text or 'ports:' not in text.split("nginx:")[1]:
        issues.append("prod_perimeter: docker-compose.prod.yml must publish nginx ports")
    return issues


def check_dev_compose_has_ports() -> list[str]:
    compose = ROOT / "docker-compose.dev.yml"
    if not compose.exists():
        return ["prod_perimeter: missing docker-compose.dev.yml"]
    text = compose.read_text(encoding="utf-8")
    required = ("gateway:", "postgres:", "nginx:")
    missing = [name for name in required if name not in text]
    if missing:
        return [f"prod_perimeter: docker-compose.dev.yml missing services: {', '.join(missing)}"]
    if text.count("ports:") < 3:
        return ["prod_perimeter: docker-compose.dev.yml should publish dev host ports"]
    return []


def main() -> int:
    errors: list[str] = []
    errors.extend(check_no_app_imports())
    errors.extend(check_no_up_auth())
    errors.extend(check_no_init_sql_mount())
    errors.extend(check_no_page_mock_imports())
    errors.extend(check_makefile_todos())
    errors.extend(check_base_compose_no_host_ports())
    errors.extend(check_prod_compose_nginx_only_ports())
    errors.extend(check_dev_compose_has_ports())

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
