from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API_URL = "http://localhost/api"
DEFAULT_CORPUS_DIR = "demo/seed_data/yandex_disk_corpus"
DEFAULT_DICTIONARY_VERSION = "mvp.v1"


def build_dictionary_zip(version: str) -> bytes:
    sources = {
        "aliases.json": ("aliases", Path("dictionaries/aliases_mvp.json")),
        "units.json": ("units", Path("dictionaries/units_mvp.json")),
        "geographies.json": ("geographies", Path("dictionaries/geographies_mvp.json")),
    }
    files: dict[str, bytes] = {}
    manifest_files = []
    for target, (kind, source) in sources.items():
        payload = json.loads(source.read_text(encoding="utf-8"))
        entries = payload.get("entries", payload.get("aliases", []))
        data = json.dumps({"entries": entries}, ensure_ascii=False, indent=2).encode("utf-8")
        files[target] = data
        manifest_files.append(
            {"path": target, "kind": kind, "sha256": hashlib.sha256(data).hexdigest()}
        )
    manifest = {
        "schema_version": "dictionary-package.v1",
        "version": version,
        "files": manifest_files,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for path, data in files.items():
            archive.writestr(path, data)
    return output.getvalue()


def edge_tls_verify() -> bool:
    return os.getenv("EDGE_TLS_VERIFY", "true").lower() not in {"0", "false", "no"}


async def login(
    client: httpx.AsyncClient,
    api_url: str,
    username: str,
    password: str,
) -> dict[str, str]:
    response = await client.post(
        f"{api_url}/auth/login",
        json={"identifier": username, "password": password},
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def ensure_dictionary(
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict[str, str],
    dictionary_version: str,
) -> dict[str, Any]:
    active = await client.get(f"{api_url}/dictionaries/active", headers=headers)
    if active.status_code == 200:
        payload = active.json()
        if payload.get("version") == dictionary_version:
            return {
                "dictionary": payload,
                "dictionary_task": {
                    "status": "completed",
                    "dictionary_version_id": payload["id"],
                },
            }
    package = build_dictionary_zip(dictionary_version)
    uploaded = await client.post(
        f"{api_url}/dictionaries/upload",
        headers=headers,
        files={"package": ("dictionary-package.zip", package, "application/zip")},
    )
    uploaded.raise_for_status()
    dictionary_task = await wait_task(
        client,
        api_url,
        headers,
        uploaded.json()["id"],
        raise_on_failed=False,
    )
    if dictionary_task.get("status") == "failed":
        listed = await client.get(f"{api_url}/dictionaries", headers=headers)
        listed.raise_for_status()
        existing = next(
            (item for item in listed.json() if item.get("version") == dictionary_version),
            None,
        )
        if existing is None:
            raise RuntimeError(
                dictionary_task.get("error_message") or "Dictionary upload failed"
            )
        version_id = existing["id"]
        dictionary_task = {
            "status": "completed",
            "dictionary_version_id": version_id,
        }
    else:
        version_id = dictionary_task["dictionary_version_id"]
    activated = await client.post(
        f"{api_url}/dictionaries/{version_id}/activate",
        headers=headers,
    )
    activated.raise_for_status()
    return {
        "dictionary": activated.json(),
        "dictionary_task": dictionary_task,
    }


async def wait_task(
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict[str, str],
    task_id: str,
    *,
    poll_timeout_seconds: int = 180,
    poll_interval_seconds: float = 1.0,
    raise_on_failed: bool = True,
) -> dict[str, Any]:
    attempts = max(1, int(poll_timeout_seconds / poll_interval_seconds))
    for _ in range(attempts):
        response = await client.get(f"{api_url}/tasks/{task_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
        if payload["status"] == "completed":
            return payload
        if payload["status"] == "failed":
            if raise_on_failed:
                raise RuntimeError(payload.get("error_message") or f"Task {task_id} failed")
            return payload
        await asyncio.sleep(poll_interval_seconds)
    raise TimeoutError(f"Task {task_id} did not complete within {poll_timeout_seconds}s")
