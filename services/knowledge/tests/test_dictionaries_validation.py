from app.api.dictionaries import DICTIONARY_FILE_KINDS, _validate_entries, _validate_file_path

from shared.contracts import DictionaryFilePayload, DictionaryPackagePayload, StoredSource


def _package(files: list[DictionaryFilePayload]) -> DictionaryPackagePayload:
    return DictionaryPackagePayload(
        version="v1",
        package_sha256="a" * 64,
        source=StoredSource(
            object_key="uploads/user/task/pkg.zip",
            original_filename="pkg.zip",
            content_type="application/zip",
            size_bytes=10,
            sha256="b" * 64,
        ),
        files=files,
    )


def test_validate_file_path_rejects_unsafe_paths() -> None:
    assert _validate_file_path("../entities.yaml") == "../entities.yaml:path_unsafe"
    assert _validate_file_path("/entities.yaml") == "/entities.yaml:path_unsafe"
    assert _validate_file_path("entities.yaml") is None


def test_validate_entries_requires_entries_and_valid_kind() -> None:
    errors = _validate_entries(
        _package(
            [
                DictionaryFilePayload(
                    path="entities.yaml",
                    kind="entities",
                    sha256="c" * 64,
                    entries=[{"canonical": "Ni", "aliases": ["nickel"]}],
                ),
                DictionaryFilePayload.model_construct(
                    path="bad.json",
                    kind="invalid",
                    sha256="d" * 64,
                    entries=[],
                ),
            ]
        )
    )
    assert "bad.json:kind_invalid" in errors
    assert "bad.json:entries_required" in errors
    assert all(kind in DICTIONARY_FILE_KINDS for kind in {"entities"})


def test_validate_entries_rejects_duplicate_paths() -> None:
    entry = {"canonical": "Ni", "aliases": []}
    errors = _validate_entries(
        _package(
            [
                DictionaryFilePayload(path="entities.yaml", kind="entities", sha256="e" * 64, entries=[entry]),
                DictionaryFilePayload(path="entities.yaml", kind="aliases", sha256="f" * 64, entries=[entry]),
            ]
        )
    )
    assert "entities.yaml:duplicate_path" in errors
