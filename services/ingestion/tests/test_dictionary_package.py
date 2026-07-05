import hashlib
import io
import json
import zipfile

import pytest
from app.service.dictionaries import DictionaryPackageError, parse_dictionary_package

from shared.contracts import StoredSource


def package_bytes(member_name: str = "aliases.json") -> bytes:
    entries = json.dumps({"entries": [{"canonical": "католит", "aliases": ["catholyte"]}]}).encode()
    manifest = {
        "schema_version": "dictionary-package.v1",
        "version": "test.v1",
        "files": [{"path": member_name, "kind": "aliases", "sha256": hashlib.sha256(entries).hexdigest()}],
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr(member_name, entries)
    return output.getvalue()


def source(content: bytes) -> StoredSource:
    return StoredSource(
        object_key="uploads/user/task/package.zip",
        original_filename="package.zip",
        content_type="application/zip",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def test_dictionary_zip_is_validated() -> None:
    content = package_bytes()
    payload = parse_dictionary_package(content, source(content), 10, 1024 * 1024)
    assert payload.version == "test.v1"
    assert payload.files[0].entries[0]["canonical"] == "католит"


def test_dictionary_zip_rejects_unsafe_path() -> None:
    content = package_bytes("../aliases.json")
    with pytest.raises(DictionaryPackageError) as error:
        parse_dictionary_package(content, source(content), 10, 1024 * 1024)
    assert error.value.code == "dictionary_zip_path_invalid"
