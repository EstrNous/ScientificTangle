#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
    ("integration", ["tests/integration"], ["services/orchestrator", "services/retrieval", "."]),
    ("e2e", ["tests/e2e"], ["."]),
]


def run_suite(name: str, testpaths: list[str], pythonpath_parts: list[str]) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(ROOT / part) for part in pythonpath_parts)
    cmd = [sys.executable, "-m", "pytest", "-q", *testpaths]
    print(f"\n=== {name} ===", flush=True)
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def main() -> int:
    failures = 0
    for name, paths, pypath in SUITES:
        if name == "e2e" and os.getenv("RUN_E2E") != "1":
            continue
        rel_paths = [str(ROOT / p) for p in paths]
        if not any(Path(p).exists() and any(Path(p).glob("test_*.py")) for p in rel_paths):
            if name in {"export", "notification", "knowledge"}:
                pass
            elif name == "e2e" and os.getenv("RUN_E2E") != "1":
                continue
        code = run_suite(name, rel_paths, pypath)
        if code != 0:
            failures += 1
    if failures:
        print(f"\n{failures} test suite(s) failed", file=sys.stderr)
        return 1
    print("\nall backend test suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
