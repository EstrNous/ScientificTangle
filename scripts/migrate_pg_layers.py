#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MIGRATION_TARGETS = (
    ("services/auth_audit", "services/auth_audit/storage"),
    ("services/orchestrator", "services/orchestrator/storage"),
    ("infra/postgres/chat_ui_db", "infra/postgres/chat_ui_db/storage"),
    ("infra/postgres/export_db", "infra/postgres/export_db/storage"),
    ("infra/postgres/notification_db", "infra/postgres/notification_db/storage"),
)


def run_alembic(cwd: Path, config_path: Path) -> None:
    env = os.environ.copy()
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(config_path), "upgrade", "head"],
        cwd=cwd,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply all PostgreSQL Alembic migrations")
    parser.parse_args()
    for workdir_rel, _ in MIGRATION_TARGETS:
        workdir = ROOT / workdir_rel
        alembic_ini = workdir / "alembic.ini"
        if not alembic_ini.exists():
            print(f"skip missing {alembic_ini}")
            continue
        print(f"migrating {workdir_rel}")
        run_alembic(workdir, alembic_ini)
    print("all pg migrations applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
