from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"


def main() -> None:
    if ENV_PATH.exists():
        return
    if not EXAMPLE_PATH.exists():
        raise SystemExit(".env.example not found")
    ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print("Created .env from .env.example")


if __name__ == "__main__":
    main()
