import hashlib
import io
import json
import zipfile
from pathlib import PurePosixPath

import yaml

from shared.contracts import DictionaryFilePayload, DictionaryPackagePayload, StoredSource


class DictionaryPackageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def parse_dictionary_package(
    content: bytes,
    source: StoredSource,
    max_entries: int,
    max_uncompressed_bytes: int,
) -> DictionaryPackagePayload:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise DictionaryPackageError("invalid_dictionary_zip", "Dictionary package must be a valid ZIP") from error
    with archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if not members or len(members) > max_entries:
            raise DictionaryPackageError("dictionary_zip_limit", "Dictionary package entry limit exceeded")
        total_size = sum(member.file_size for member in members)
        if total_size > max_uncompressed_bytes:
            raise DictionaryPackageError("dictionary_zip_limit", "Dictionary package size limit exceeded")
        members_by_name = {_safe_member_name(member.filename): member for member in members}
        if len(members_by_name) != len(members):
            raise DictionaryPackageError("dictionary_zip_path_invalid", "Dictionary package contains duplicate paths")
        if "manifest.json" not in members_by_name:
            raise DictionaryPackageError("dictionary_manifest_missing", "Dictionary package must contain manifest.json")
        manifest = _load_json(_read_member(archive, members_by_name["manifest.json"]), "manifest.json")
        if manifest.get("schema_version") != "dictionary-package.v1":
            raise DictionaryPackageError("dictionary_schema_unsupported", "Unsupported dictionary package schema")
        version = str(manifest.get("version", "")).strip()
        if not version:
            raise DictionaryPackageError("dictionary_version_missing", "Dictionary package version is required")
        files = []
        declared = manifest.get("files")
        if not isinstance(declared, list) or not declared:
            raise DictionaryPackageError("dictionary_manifest_invalid", "Dictionary manifest files are required")
        seen_paths: set[str] = set()
        for item in declared:
            if not isinstance(item, dict):
                raise DictionaryPackageError("dictionary_manifest_invalid", "Dictionary file descriptor is invalid")
            path = _safe_member_name(str(item.get("path", "")))
            kind = str(item.get("kind", ""))
            checksum = str(item.get("sha256", ""))
            if path in seen_paths or path not in members_by_name or kind not in {"entities", "aliases", "units", "geographies"}:
                raise DictionaryPackageError("dictionary_manifest_invalid", "Dictionary file declaration is invalid")
            seen_paths.add(path)
            data = _read_member(archive, members_by_name[path])
            if hashlib.sha256(data).hexdigest() != checksum:
                raise DictionaryPackageError("dictionary_checksum_mismatch", f"Checksum mismatch for {path}")
            payload = _load_data(data, path)
            entries = payload.get("entries") if isinstance(payload, dict) else payload
            if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
                raise DictionaryPackageError("dictionary_file_invalid", f"Dictionary entries are invalid in {path}")
            files.append(DictionaryFilePayload(path=path, kind=kind, sha256=checksum, entries=entries))
        return DictionaryPackagePayload(
            version=version,
            package_sha256=hashlib.sha256(content).hexdigest(),
            source=source,
            files=files,
        )


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise DictionaryPackageError("dictionary_zip_path_invalid", "Dictionary package contains an unsafe path")
    return str(path)


def _load_data(data: bytes, path: str):
    if path.lower().endswith((".yaml", ".yml")):
        try:
            return yaml.safe_load(data.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as error:
            raise DictionaryPackageError("dictionary_file_invalid", f"Invalid YAML in {path}") from error
    return _load_json(data, path)


def _read_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> bytes:
    try:
        return archive.read(member)
    except (RuntimeError, zipfile.BadZipFile) as error:
        raise DictionaryPackageError("invalid_dictionary_zip", "Dictionary package is corrupted") from error


def _load_json(data: bytes, path: str):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DictionaryPackageError("dictionary_file_invalid", f"Invalid JSON in {path}") from error
