import argparse
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


async def wait_task(client: httpx.AsyncClient, api_url: str, headers: dict[str, str], task_id: str) -> dict[str, Any]:
    for _ in range(180):
        response = await client.get(f"{api_url}/tasks/{task_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
        if payload["status"] == "completed":
            return payload
        if payload["status"] == "failed":
            raise RuntimeError(payload.get("error_message") or f"Task {task_id} failed")
        await asyncio.sleep(1)
    raise TimeoutError(f"Task {task_id} did not complete")


async def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    corpus_root = Path(args.corpus_dir)
    corpus_files = [path for path in corpus_root.rglob("*") if path.is_file() and path.name != "manifest.json"]
    if not corpus_files:
        raise SystemExit(f"Real demo corpus is missing in {corpus_root}")
    verify_tls = os.getenv("EDGE_TLS_VERIFY", "true").lower() not in {"0", "false", "no"}
    async with httpx.AsyncClient(timeout=180.0, verify=verify_tls) as client:
        login = await client.post(
            f"{args.api_url}/auth/login",
            json={"identifier": args.username, "password": args.password},
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        package = build_dictionary_zip(args.dictionary_version)
        uploaded = await client.post(
            f"{args.api_url}/dictionaries/upload",
            headers=headers,
            files={"package": ("dictionary-package.zip", package, "application/zip")},
        )
        uploaded.raise_for_status()
        dictionary_task = await wait_task(client, args.api_url, headers, uploaded.json()["id"])
        version_id = dictionary_task["dictionary_version_id"]
        activated = await client.post(
            f"{args.api_url}/dictionaries/{version_id}/activate",
            headers=headers,
        )
        activated.raise_for_status()
        handles = [path.open("rb") for path in corpus_files]
        try:
            documents = await client.post(
                f"{args.api_url}/documents/upload",
                headers=headers,
                files=[("files", (path.name, handle, "application/octet-stream")) for path, handle in zip(corpus_files, handles, strict=True)],
            )
            documents.raise_for_status()
        finally:
            for handle in handles:
                handle.close()
        document_task = await wait_task(client, args.api_url, headers, documents.json()["id"])
        return {
            "dictionary": activated.json(),
            "dictionary_task": dictionary_task,
            "document_task": document_task,
            "corpus_files": len(corpus_files),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--dictionary-version", default=DEFAULT_DICTIONARY_VERSION)
    parser.add_argument("--username", default=os.getenv("DEMO_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("DEMO_ADMIN_PASSWORD", "admin123"))
    return parser.parse_args()


def main() -> None:
    print(json.dumps(asyncio.run(run_demo(parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
