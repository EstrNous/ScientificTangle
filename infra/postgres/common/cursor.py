from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CursorPage:
    items: list[Any]
    next_cursor: str | None


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    normalized = created_at.astimezone(UTC).isoformat()
    return f"{normalized}|{item_id}"


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    created_at_raw, item_id_raw = cursor.split("|", 1)
    return datetime.fromisoformat(created_at_raw), UUID(item_id_raw)
