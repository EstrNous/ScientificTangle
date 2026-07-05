from __future__ import annotations

import argparse
import os

import httpx


def fetch_token(base_url: str, username: str, password: str) -> str:
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/auth/login",
        json={"identifier": username, "password": password},
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth-url", default=os.getenv("AUTH_URL", "http://localhost:8001"))
    parser.add_argument("--username", default=os.getenv("AUTH_SEED_RESEARCHER_USERNAME", "researcher"))
    parser.add_argument("--password", default=os.getenv("AUTH_SEED_RESEARCHER_PASSWORD", "researcher"))
    args = parser.parse_args()
    token = fetch_token(args.auth_url, args.username, args.password)
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
