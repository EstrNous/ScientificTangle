#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COVERAGE_PACKAGES: dict[str, list[str]] = {
    "shared": ["shared"],
    "auth_audit": ["services/auth_audit/app"],
    "gateway": ["services/gateway/app"],
    "orchestrator": ["services/orchestrator/app", "infra/postgres/orchestrator_db"],
    "ingestion": ["services/ingestion/app"],
    "knowledge": ["services/knowledge/app", "services/knowledge/adapters"],
    "retrieval": ["services/retrieval/app"],
    "model": ["services/model/app"],
    "export": ["services/export/app"],
    "notification": ["services/notification/app"],
    "integration": ["eval"],
    "performance": ["scripts"],
}

SUITES: list[tuple[str, list[str], list[str]]] = [
    ("shared", ["shared/tests"], ["."]),
    ("auth_audit", ["services/auth_audit/tests"], ["services/auth_audit", "."]),
    ("gateway", ["services/gateway/tests"], ["services/gateway", "."]),
    ("orchestrator", ["services/orchestrator/tests"], ["services/orchestrator", "."]),
    ("ingestion", ["services/ingestion/tests"], ["services/ingestion", "."]),
    ("knowledge", ["services/knowledge/tests"], ["services/knowledge", "."]),
    ("retrieval", ["services/retrieval/tests"], ["services/retrieval", "."]),
    ("model", ["services/model/tests"], ["services/model", "."]),
    ("export", ["services/export/tests"], ["services/export", "."]),
    ("notification", ["services/notification/tests"], ["services/notification", "."]),
    ("integration", ["tests/integration"], ["services/orchestrator", "services/retrieval", "services/knowledge", "."]),
    ("performance", ["tests/performance"], ["services/orchestrator", "services/retrieval", "services/knowledge", "."]),
    ("e2e", ["tests/e2e"], ["."]),
]


def run_suite(
    name: str,
    testpaths: list[str],
    pythonpath_parts: list[str],
    *,
    coverage: bool,
    model_coverage: bool,
) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(ROOT / part) for part in pythonpath_parts)
    cmd = [sys.executable, "-m", "pytest", "-q", *testpaths]
    if coverage:
        for package in COVERAGE_PACKAGES.get(name, []):
            if name == "model" and not model_coverage:
                continue
            cmd.extend(["--cov", package, "--cov-append"])
    print(f"\n=== {name} ===", flush=True)
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def report_coverage(fail_under: int, *, include_model: bool) -> int:
    omit = "*/tests/*,*/__pycache__/*"
    if not include_model:
        omit += ",services/model/*"
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "report",
        "--fail-under",
        str(fail_under),
        "--omit",
        omit,
    ]
    print("\n=== coverage ===", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    coverage = os.getenv("COVERAGE") == "1"
    coverage_threshold = int(os.getenv("COVERAGE_FAIL_UNDER", "60"))
    if coverage:
        coverage_data = ROOT / ".coverage"
        if coverage_data.exists():
            coverage_data.unlink()
    model_coverage = os.getenv("RUN_MODEL_TESTS") == "1"

    failures = 0
    for name, paths, pypath in SUITES:
        if name == "e2e" and os.getenv("RUN_E2E") != "1":
            continue
        if name == "model" and os.getenv("RUN_MODEL_TESTS") != "1":
            print("\n=== model (skipped, set RUN_MODEL_TESTS=1) ===", flush=True)
            continue
        rel_paths = [str(ROOT / p) for p in paths]
        if not any(Path(p).exists() and any(Path(p).glob("test_*.py")) for p in rel_paths):
            if name in {"export", "notification", "knowledge"}:
                pass
            elif name == "e2e" and os.getenv("RUN_E2E") != "1":
                continue
        if name == "integration":
            suites = [
                (
                    [str(ROOT / "tests/integration/test_orchestrator_ingestion_offline.py")],
                    ["services/orchestrator", "."],
                ),
                (
                    [
                        str(ROOT / "tests/integration"),
                        "--ignore=tests/integration/test_orchestrator_ingestion_offline.py",
                    ],
                    ["services/orchestrator", "services/retrieval", "services/knowledge", "."],
                ),
            ]
            for testpaths, pythonpath_parts in suites:
                code = run_suite(f"{name}", testpaths, pythonpath_parts, coverage=coverage, model_coverage=model_coverage)
                if code != 0:
                    failures += 1
            continue
        code = run_suite(name, rel_paths, pypath, coverage=coverage, model_coverage=model_coverage)
        if code != 0:
            failures += 1
    if failures:
        print(f"\n{failures} test suite(s) failed", file=sys.stderr)
        return 1
    if coverage:
        coverage_code = report_coverage(coverage_threshold, include_model=model_coverage)
        if coverage_code != 0:
            print("\ncoverage threshold failed", file=sys.stderr)
            return coverage_code
    print("\nall backend test suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
