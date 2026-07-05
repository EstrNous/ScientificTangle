import argparse
import hashlib
from pathlib import Path

import httpx


PUBLIC_RESOURCES_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
DEFAULT_PUBLIC_URL = "https://disk.yandex.ru/d/npigiuw4Rbe9Pg"


def list_public_files(public_key: str) -> list[dict]:
    files = []
    queue = ["/"]
    with httpx.Client(timeout=60.0) as client:
        while queue:
            path = queue.pop(0)
            response = client.get(
                PUBLIC_RESOURCES_URL,
                params={"public_key": public_key, "path": path, "limit": 1000},
            )
            response.raise_for_status()
            resource = response.json()
            embedded = resource.get("_embedded", {})
            for item in embedded.get("items", []):
                if item.get("type") == "dir":
                    queue.append(item["path"])
                elif item.get("type") == "file":
                    files.append(item)
    return files


def download_file(public_key: str, resource_path: str, output_root: Path) -> Path:
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        response = client.get(
            f"{PUBLIC_RESOURCES_URL}/download",
            params={"public_key": public_key, "path": resource_path},
        )
        response.raise_for_status()
        href = response.json()["href"]
        data = client.get(href)
        data.raise_for_status()
    relative_path = Path(resource_path.lstrip("/"))
    target = output_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.content)
    return target


def build_manifest(files: list[dict], downloaded: list[Path], output_root: Path) -> dict:
    manifest_items = []
    for item, path in zip(files, downloaded):
        data = path.read_bytes()
        manifest_items.append(
            {
                "name": item.get("name"),
                "source_path": item.get("path"),
                "local_path": str(path.relative_to(output_root)).replace("\\", "/"),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mime_type": item.get("mime_type"),
            }
        )
    return {"source": DEFAULT_PUBLIC_URL, "files": manifest_items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-url", default=DEFAULT_PUBLIC_URL)
    parser.add_argument("--output-dir", default="demo/seed_data/yandex_disk_corpus")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_dir)
    public_key = args.public_url
    files = list_public_files(public_key)
    selected = files[: args.limit] if args.limit else files
    downloaded = [download_file(public_key, item["path"], output_root) for item in selected]
    manifest = build_manifest(selected, downloaded, output_root)
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(__import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Downloaded {len(downloaded)} files to {output_root}")


if __name__ == "__main__":
    main()
