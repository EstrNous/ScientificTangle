from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / ".env"

POSTGRES_URL_KEYS = (
    "POSTGRES_URL",
    "AUTH_DATABASE_URL",
    "GATEWAY_DATABASE_URL",
)


def postgres_async_url(password: str) -> str:
    return f"postgresql+asyncpg://st_user:{quote(password, safe='')}@postgres:5432/scientific_tangle"


def password_from_url(url: str) -> str:
    if not url:
        return ""
    return unquote(urlparse(url).password or "")


def read_env(path: Path) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        raise SystemExit(f".env not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value
    return lines, values


def write_env(path: Path, lines: list[str], values: dict[str, str]) -> None:
    updated: list[str] = []
    seen: set[str] = set()
    prefix_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
    for line in lines:
        match = prefix_pattern.match(line)
        if not match:
            updated.append(line)
            continue
        key = match.group(1)
        if key in values:
            updated.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            updated.append(line)
    for key in (*POSTGRES_URL_KEYS, "POSTGRES_PASSWORD"):
        if key in values and key not in seen:
            updated.append(f"{key}={values[key]}")
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def sync_postgres_urls(values: dict[str, str]) -> bool:
    password = values.get("POSTGRES_PASSWORD", "").strip()
    if not password:
        raise SystemExit("POSTGRES_PASSWORD is empty in .env")
    target_url = postgres_async_url(password)
    changed = False
    for key in POSTGRES_URL_KEYS:
        if values.get(key) != target_url:
            values[key] = target_url
            changed = True
    return changed


def compose_command(compose_files: list[str], *args: str) -> list[str]:
    command = ["docker", "compose"]
    for compose_file in compose_files:
        command.extend(["-f", compose_file])
    command.extend(args)
    return command


def verify_postgres_tcp(password: str, compose_files: list[str]) -> bool:
    if not password:
        return False
    command = compose_command(
        compose_files,
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={password}",
        "postgres",
        "psql",
        "-h",
        "127.0.0.1",
        "-U",
        "st_user",
        "-d",
        "scientific_tangle",
        "-tAc",
        "SELECT 1",
    )
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0


def alter_postgres_password(password: str, compose_files: list[str]) -> bool:
    escaped = password.replace("'", "''")
    command = compose_command(
        compose_files,
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "st_user",
        "-d",
        "scientific_tangle",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        f"ALTER USER st_user WITH PASSWORD '{escaped}';",
    )
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "ALTER USER failed\n")
    return result.returncode == 0


def collect_candidate_passwords(values: dict[str, str]) -> list[str]:
    candidates: list[str] = []
    for raw in (
        password_from_url(values.get("AUTH_DATABASE_URL", "")),
        values.get("POSTGRES_PASSWORD", ""),
        password_from_url(values.get("POSTGRES_URL", "")),
        "st_pass",
    ):
        if raw and raw not in candidates:
            candidates.append(raw)
    return candidates


def repair_postgres_env(env_path: Path, compose_files: list[str], *, sync_only: bool) -> None:
    lines, values = read_env(env_path)
    changed = sync_postgres_urls(values)
    if changed:
        write_env(env_path, lines, values)
        print(f"Synced postgres URLs in {env_path}")

    if sync_only:
        return

    if not compose_files:
        raise SystemExit("compose files are required unless --sync-urls-only is set")

    for candidate in collect_candidate_passwords(values):
        if verify_postgres_tcp(candidate, compose_files):
            if values.get("POSTGRES_PASSWORD") != candidate:
                print(f"PostgreSQL TCP OK with stored password; aligning POSTGRES_PASSWORD")
                values["POSTGRES_PASSWORD"] = candidate
                sync_postgres_urls(values)
                write_env(env_path, lines, values)
            else:
                print("PostgreSQL TCP auth OK for POSTGRES_PASSWORD")
            return

    postgres_password = values["POSTGRES_PASSWORD"]
    print("PostgreSQL TCP auth failed for all known passwords; running ALTER USER", file=sys.stderr)
    if not alter_postgres_password(postgres_password, compose_files):
        raise SystemExit("ALTER USER failed; postgres password could not be aligned with .env")

    sync_postgres_urls(values)
    write_env(env_path, lines, values)

    if verify_postgres_tcp(postgres_password, compose_files):
        print("PostgreSQL password updated and verified (TCP)")
        return

    auth_url_password = password_from_url(values.get("AUTH_DATABASE_URL", ""))
    raise SystemExit(
        "PostgreSQL password still rejected after repair.\n"
        f"POSTGRES_PASSWORD={postgres_password!r}\n"
        f"AUTH_DATABASE_URL password={auth_url_password!r}\n"
        "Check: grep -E 'POSTGRES_PASSWORD|AUTH_DATABASE_URL' .env\n"
        "Then: docker inspect st-auth-audit --format '{{range .Config.Env}}{{println .}}{{end}}' | grep AUTH_DATABASE_URL"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync postgres URLs in .env and repair DB password drift")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="Path to .env")
    parser.add_argument(
        "--compose-file",
        action="append",
        default=[],
        dest="compose_files",
        help="docker compose file (-f), repeatable",
    )
    parser.add_argument(
        "--sync-urls-only",
        action="store_true",
        help="Only rewrite postgres URLs in .env; do not talk to docker",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repair_postgres_env(
        Path(args.env),
        args.compose_files,
        sync_only=args.sync_urls_only,
    )


if __name__ == "__main__":
    main()
